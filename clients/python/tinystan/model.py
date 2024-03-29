import contextlib
import ctypes
import sys
import warnings
from enum import Enum
from os import PathLike, fspath
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from dllist import dllist
from numpy.ctypeslib import ndpointer
from stanio import dump_stan_json

from .compile import compile_model, windows_dll_path_setup
from .output import StanOutput
from .util import validate_readable


def wrapped_ndptr(*args, **kwargs):
    """
    A version of np.ctypeslib.ndpointer
    which allows None (passed as NULL)
    """
    base = ndpointer(*args, **kwargs)

    def from_param(_cls, obj):
        if obj is None:
            return obj
        return base.from_param(obj)

    return type(base.__name__, (base,), {"from_param": classmethod(from_param)})


double_array = ndpointer(dtype=ctypes.c_double, flags=("C_CONTIGUOUS"))
nullable_double_array = wrapped_ndptr(dtype=ctypes.c_double, flags=("C_CONTIGUOUS"))
err_ptr = ctypes.POINTER(ctypes.c_void_p)
print_callback_type = ctypes.CFUNCTYPE(
    None, ctypes.POINTER(ctypes.c_char), ctypes.c_size_t, ctypes.c_bool
)


@print_callback_type
def print_callback(msg, size, is_error):
    print(
        ctypes.string_at(msg, size).decode("utf-8"),
        file=sys.stderr if is_error else sys.stdout,
    )


HMC_SAMPLER_VARIABLES = [
    "lp__",
    "accept_stat__",
    "stepsize__",
    "treedepth__",
    "n_leapfrog__",
    "divergent__",
    "energy__",
]

PATHFINDER_VARIABLES = [
    "lp_approx__",
    "lp__",
]

OPTIMIZE_VARIABLES = [
    "lp__",
]

LAPLACE_VARIABLES = [
    "log_p__",
    "log_q__",
]

FIXED_SAMPLER_VARIABLES = [
    "lp__",
    "accept_stat__",
]


class HMCMetric(Enum):
    UNIT = 0
    DENSE = 1
    DIAGONAL = 2


class OptimizationAlgorithm(Enum):
    NEWTON = 0
    BFGS = 1
    LBFGS = 2


_exception_types = [RuntimeError, ValueError, KeyboardInterrupt]


# also allow inits from a StanOutput
def encode_stan_json(data: Union[str, PathLike, Dict[str, Any]]) -> bytes:
    """Turn the provided data into something we can send to C++."""
    if isinstance(data, PathLike):
        validate_readable(data)
        return fspath(data).encode()
    if isinstance(data, str):
        return data.encode()
    return dump_stan_json(data).encode()


def rand_u32():
    return np.random.randint(0, 2**32 - 1, dtype=np.uint32)


def preprocess_laplace_inputs(
    mode: Union[StanOutput, np.ndarray, Dict[str, Any], str, PathLike]
) -> Tuple[Optional[np.ndarray], Optional[str]]:
    if isinstance(mode, StanOutput):
        # handle case of passing optimization output directly
        if len(mode.data.shape) == 1:
            mode = mode.data[1:]
        else:
            raise ValueError("Laplace can only be used with Optimization output")
            # mode = mode.create_inits(chains=1, seed=seed)

    if isinstance(mode, np.ndarray):
        mode_json = None
        mode_array = mode
    else:
        mode_json = encode_stan_json(mode)
        mode_array = None

    return mode_array, mode_json


class Model:
    def __init__(
        self,
        model: Union[str, PathLike],
        *,
        capture_stan_prints: bool = True,
        stanc_args: List[str] = [],
        make_args: List[str] = [],
        warn: bool = True,
    ):
        windows_dll_path_setup()

        model = fspath(model)
        if model.endswith(".stan"):
            self.lib_path = compile_model(
                model, stanc_args=stanc_args, make_args=make_args
            )
        else:
            self.lib_path = model

        if warn and self.lib_path in dllist():
            warnings.warn(
                f"Loading a shared object {self.lib_path} that has already been loaded.\n"
                "If the file has changed since the last time it was loaded, this load may "
                "not update the library!"
            )

        self._lib = ctypes.CDLL(self.lib_path)

        self._create_model = self._lib.tinystan_create_model
        self._create_model.restype = ctypes.c_void_p
        self._create_model.argtypes = [ctypes.c_char_p, ctypes.c_uint, err_ptr]

        self._delete_model = self._lib.tinystan_destroy_model
        self._delete_model.restype = None
        self._delete_model.argtypes = [ctypes.c_void_p]

        self._get_param_names = self._lib.tinystan_model_param_names
        self._get_param_names.restype = ctypes.c_char_p
        self._get_param_names.argtypes = [ctypes.c_void_p]

        self._num_free_params = self._lib.tinystan_model_num_free_params
        self._num_free_params.restype = ctypes.c_size_t
        self._num_free_params.argtypes = [ctypes.c_void_p]

        self._version = self._lib.tinystan_api_version
        self._version.restype = None
        self._version.argtypes = [
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_int),
        ]

        self._ffi_sample = self._lib.tinystan_sample
        self._ffi_sample.restype = ctypes.c_int
        self._ffi_sample.argtypes = [
            ctypes.c_void_p,  # model
            ctypes.c_size_t,  # num_chains
            ctypes.c_char_p,  # inits
            ctypes.c_uint,  # seed
            ctypes.c_uint,  # id
            ctypes.c_double,  # init_radius
            ctypes.c_int,  # num_warmup
            ctypes.c_int,  # num_samples
            ctypes.c_int,  # really enum for metric
            nullable_double_array,  # metric init in
            # adaptation
            ctypes.c_bool,  # adapt
            ctypes.c_double,  # delta
            ctypes.c_double,  # gamma
            ctypes.c_double,  # kappa
            ctypes.c_double,  # t0
            ctypes.c_uint,  # init_buffer
            ctypes.c_uint,  # term_buffer
            ctypes.c_uint,  # window
            ctypes.c_bool,  # save_warmup
            ctypes.c_double,  # stepsize
            ctypes.c_double,  # stepsize_jitter
            ctypes.c_int,  # max_depth
            ctypes.c_int,  # refresh
            ctypes.c_int,  # num_threads
            double_array,
            ctypes.c_size_t,  # buffer size
            nullable_double_array,  # metric out
            err_ptr,
        ]

        self._ffi_pathfinder = self._lib.tinystan_pathfinder
        self._ffi_pathfinder.restype = ctypes.c_int
        self._ffi_pathfinder.argtypes = [
            ctypes.c_void_p,  # model
            ctypes.c_size_t,  # num_paths
            ctypes.c_char_p,  # inits
            ctypes.c_uint,  # seed
            ctypes.c_uint,  # id
            ctypes.c_double,  # init_radius
            ctypes.c_int,  # num_draws
            ctypes.c_int,  # max_history_size
            ctypes.c_double,  # init_alpha
            ctypes.c_double,  # tol_obj
            ctypes.c_double,  # tol_rel_obj
            ctypes.c_double,  # tol_grad
            ctypes.c_double,  # tol_rel_grad
            ctypes.c_double,  # tol_param
            ctypes.c_int,  # num_iterations
            ctypes.c_int,  # num_elbo_draws
            ctypes.c_int,  # num_multi_draws
            ctypes.c_bool,  # calculate_lp
            ctypes.c_bool,  # psis_resample
            ctypes.c_int,  # refresh
            ctypes.c_int,  # num_threads
            double_array,  # output samples
            ctypes.c_size_t,  # buffer size
            err_ptr,
        ]

        self._ffi_optimize = self._lib.tinystan_optimize
        self._ffi_optimize.restype = ctypes.c_int
        self._ffi_optimize.argtypes = [
            ctypes.c_void_p,  # model
            ctypes.c_char_p,  # inits
            ctypes.c_uint,  # seed
            ctypes.c_uint,  # id
            ctypes.c_double,  # init_radius
            ctypes.c_int,  # really enum for algorithm
            ctypes.c_int,  # num_iterations
            ctypes.c_bool,  # jacobian
            ctypes.c_int,  # max_history_size
            ctypes.c_double,  # init_alpha
            ctypes.c_double,  # tol_obj
            ctypes.c_double,  # tol_rel_obj
            ctypes.c_double,  # tol_grad
            ctypes.c_double,  # tol_rel_grad
            ctypes.c_double,  # tol_param
            ctypes.c_int,  # refresh
            ctypes.c_int,  # num_threads
            double_array,
            ctypes.c_size_t,  # buffer size
            err_ptr,
        ]

        self._ffi_laplace = self._lib.tinystan_laplace_sample
        self._ffi_laplace.restype = ctypes.c_int
        self._ffi_laplace.argtypes = [
            ctypes.c_void_p,  # model
            nullable_double_array,  # array of constrained params
            ctypes.c_char_p,  # json of constrained params
            ctypes.c_uint,  # seed
            ctypes.c_int,  # draws
            ctypes.c_bool,  # jacobian
            ctypes.c_bool,  # calculate_lp
            ctypes.c_int,  # refresh
            ctypes.c_int,  # num_threads
            double_array,  # draws buffer
            ctypes.c_size_t,  # buffer size
            nullable_double_array,  # hessian out
            err_ptr,
        ]

        self._get_error_msg = self._lib.tinystan_get_error_message
        self._get_error_msg.restype = ctypes.c_char_p
        self._get_error_msg.argtypes = [ctypes.c_void_p]
        self._get_error_type = self._lib.tinystan_get_error_type
        self._get_error_type.restype = ctypes.c_int  # really enum
        self._get_error_type.argtypes = [ctypes.c_void_p]
        self._free_error = self._lib.tinystan_free_stan_error
        self._free_error.restype = None
        self._free_error.argtypes = [ctypes.c_void_p]

        get_separator = self._lib.tinystan_separator_char
        get_separator.restype = ctypes.c_char
        get_separator.argtypes = []
        self.sep = get_separator()

        if capture_stan_prints:
            set_print_callback = self._lib.tinystan_set_print_callback
            set_print_callback.restype = None
            set_print_callback.argtypes = [print_callback_type]
            set_print_callback(print_callback)

    def _raise_for_error(self, rc: int, err):
        if rc != 0:
            if err.contents:
                msg = self._get_error_msg(err.contents).decode("utf-8")
                exception_type = self._get_error_type(err.contents)
                self._free_error(err.contents)
                exn = _exception_types[exception_type]
                raise exn(msg)
            else:
                raise RuntimeError(f"Unknown error, function returned code {rc}")

    @contextlib.contextmanager
    def _get_model(self, data, seed):
        err = ctypes.pointer(ctypes.c_void_p())

        model = self._create_model(encode_stan_json(data), seed, err)
        self._raise_for_error(not model, err)
        try:
            yield model
        finally:
            self._delete_model(model)

    def _encode_inits(self, inits, chains, seed):
        inits_encoded = None
        if inits is not None:
            if isinstance(inits, StanOutput):
                inits = inits.create_inits(chains=chains, seed=seed)

            if isinstance(inits, list):
                inits_encoded = self.sep.join(encode_stan_json(init) for init in inits)
            else:
                inits_encoded = encode_stan_json(inits)
        return inits_encoded

    def _get_parameter_names(self, model):
        comma_separated = self._get_param_names(model).decode("utf-8").strip()
        if comma_separated == "":
            return []
        return list(comma_separated.split(","))

    def api_version(self):
        major, minor, patch = ctypes.c_int(), ctypes.c_int(), ctypes.c_int()
        self._version(ctypes.byref(major), ctypes.byref(minor), ctypes.byref(patch))
        return (major.value, minor.value, patch.value)

    def sample(
        self,
        data="",
        *,
        num_chains=4,
        inits=None,
        seed=None,
        id=1,
        init_radius=2.0,
        num_warmup=1000,
        num_samples=1000,
        metric=HMCMetric.DIAGONAL,
        init_inv_metric=None,
        save_metric=False,
        adapt=True,
        delta=0.8,
        gamma=0.05,
        kappa=0.75,
        t0=10,
        init_buffer=75,
        term_buffer=50,
        window=25,
        save_warmup=False,
        stepsize=1.0,
        stepsize_jitter=0.0,
        max_depth=10,
        refresh=0,
        num_threads=-1,
    ):
        # these are checked here because they're sizes for "out"
        if num_chains < 1:
            raise ValueError("num_chains must be at least 1")
        if num_warmup < 0:
            raise ValueError("num_warmup must be non-negative")
        if num_samples < 1:
            raise ValueError("num_samples must be at least 1")

        seed = seed or rand_u32()

        with self._get_model(data, seed) as model:
            model_params = self._num_free_params(model)
            if model_params == 0:
                raise ValueError("Model has no parameters to sample.")

            param_names = HMC_SAMPLER_VARIABLES + self._get_parameter_names(model)

            num_params = len(param_names)
            num_draws = num_samples + num_warmup * save_warmup
            out = np.zeros((num_chains, num_draws, num_params), dtype=np.float64)

            metric_size = (
                (model_params, model_params)
                if metric == HMCMetric.DENSE
                else (model_params,)
            )

            if init_inv_metric is not None:
                if init_inv_metric.shape == metric_size:
                    init_inv_metric = np.repeat(
                        init_inv_metric[np.newaxis], num_chains, axis=0
                    )
                elif init_inv_metric.shape == (num_chains, *metric_size):
                    pass
                else:
                    raise ValueError(
                        f"Invalid initial metric size. Expected a {metric_size} "
                        f"or {(num_chains, *metric_size)} matrix."
                    )

            if save_metric:
                metric_out = np.zeros((num_chains, *metric_size), dtype=np.float64)
            else:
                metric_out = None

            err = ctypes.pointer(ctypes.c_void_p())
            rc = self._ffi_sample(
                model,
                num_chains,
                self._encode_inits(inits, num_chains, seed),
                seed,
                id,
                init_radius,
                num_warmup,
                num_samples,
                metric.value,
                init_inv_metric,
                adapt,
                delta,
                gamma,
                kappa,
                t0,
                init_buffer,
                term_buffer,
                window,
                save_warmup,
                stepsize,
                stepsize_jitter,
                max_depth,
                refresh,
                num_threads,
                out,
                out.size,
                metric_out,
                err,
            )
            self._raise_for_error(rc, err)

        output = StanOutput(param_names, out)
        if save_metric:
            output.metric = metric_out
        return output

    def pathfinder(
        self,
        data="",
        *,
        num_paths=4,
        inits=None,
        seed=None,
        id=1,
        init_radius=2.0,
        num_draws=1000,
        max_history_size=5,
        init_alpha=0.001,
        tol_obj=1e-12,
        tol_rel_obj=1e4,
        tol_grad=1e-8,
        tol_rel_grad=1e7,
        tol_param=1e-8,
        num_iterations=1000,
        num_elbo_draws=100,
        num_multi_draws=1000,
        calculate_lp=True,
        psis_resample=True,
        refresh=0,
        num_threads=-1,
    ):
        if num_draws < 1:
            raise ValueError("num_draws must be at least 1")
        if num_paths < 1:
            raise ValueError("num_paths must be at least 1")
        if num_multi_draws < 1:
            raise ValueError("num_multi_draws must be at least 1")

        if calculate_lp and psis_resample:
            output_size = num_multi_draws
        else:
            output_size = num_draws * num_paths

        seed = seed or rand_u32()

        with self._get_model(data, seed) as model:
            model_params = self._num_free_params(model)
            if model_params == 0:
                raise ValueError("Model has no parameters.")

            param_names = PATHFINDER_VARIABLES + self._get_parameter_names(model)

            num_params = len(param_names)
            out = np.zeros((output_size, num_params), dtype=np.float64)

            err = ctypes.pointer(ctypes.c_void_p())
            rc = self._ffi_pathfinder(
                model,
                num_paths,
                self._encode_inits(inits, num_paths, seed),
                seed,
                id,
                init_radius,
                num_draws,
                max_history_size,
                init_alpha,
                tol_obj,
                tol_rel_obj,
                tol_grad,
                tol_rel_grad,
                tol_param,
                num_iterations,
                num_elbo_draws,
                num_multi_draws,
                calculate_lp,
                psis_resample,
                refresh,
                num_threads,
                out,
                out.size,
                err,
            )
            self._raise_for_error(rc, err)

        return StanOutput(param_names, out)

    def optimize(
        self,
        data="",
        *,
        init=None,
        seed=None,
        id=1,
        init_radius=2.0,
        algorithm=OptimizationAlgorithm.LBFGS,
        jacobian=False,
        num_iterations=2000,
        max_history_size=5,
        init_alpha=0.001,
        tol_obj=1e-12,
        tol_rel_obj=1e4,
        tol_grad=1e-8,
        tol_rel_grad=1e7,
        tol_param=1e-8,
        refresh=0,
        num_threads=-1,
    ):
        seed = seed or rand_u32()

        with self._get_model(data, seed) as model:
            param_names = OPTIMIZE_VARIABLES + self._get_parameter_names(model)

            num_params = len(param_names)
            out = np.zeros(num_params, dtype=np.float64)

            err = ctypes.pointer(ctypes.c_void_p())
            rc = self._ffi_optimize(
                model,
                self._encode_inits(init, 1, seed),
                seed,
                id,
                init_radius,
                algorithm.value,
                num_iterations,
                jacobian,
                max_history_size,
                init_alpha,
                tol_obj,
                tol_rel_obj,
                tol_grad,
                tol_rel_grad,
                tol_param,
                refresh,
                num_threads,
                out,
                out.size,
                err,
            )
            self._raise_for_error(rc, err)

        return StanOutput(param_names, out)

    def laplace_sample(
        self,
        mode,
        data="",
        *,
        num_draws=1000,
        jacobian=True,
        calculate_lp=True,
        save_hessian=False,
        seed=None,
        refresh=0,
        num_threads=-1,
    ):
        if num_draws < 1:
            raise ValueError("num_draws must be at least 1")

        seed = seed or rand_u32()

        mode_array, mode_json = preprocess_laplace_inputs(mode)

        with self._get_model(data, seed) as model:
            param_names = LAPLACE_VARIABLES + self._get_parameter_names(model)
            num_params = len(param_names)

            if mode_array is not None and len(mode_array) != num_params - len(
                LAPLACE_VARIABLES
            ):
                raise ValueError(
                    f"Mode array has incorrect length. Expected {num_params - len(LAPLACE_VARIABLES)}"
                    f" but got {len(mode_array)}"
                )

            out = np.zeros((num_draws, num_params), dtype=np.float64)

            model_params = self._num_free_params(model)
            hessian_out = (
                np.zeros((model_params, model_params), dtype=np.float64)
                if save_hessian
                else None
            )
            err = ctypes.pointer(ctypes.c_void_p())

            rc = self._ffi_laplace(
                model,
                mode_array,
                mode_json,
                seed,
                num_draws,
                jacobian,
                calculate_lp,
                refresh,
                num_threads,
                out,
                out.size,
                hessian_out,
                err,
            )
            self._raise_for_error(rc, err)

        output = StanOutput(param_names, out)
        if save_hessian:
            output.hessian = hessian_out
        return output
