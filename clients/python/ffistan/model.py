import ctypes
import subprocess
from enum import Enum
import contextlib
from typing import Any, Dict, Union

import numpy as np
from numpy.ctypeslib import ndpointer

from stanio import dump_stan_json
from .output import StanOutput

double_array = ndpointer(dtype=ctypes.c_double, flags=("C_CONTIGUOUS"))


def wrapped_ndptr(*args, **kwargs):
    """
    A version of np.ctypeslib.ndpointer
    which allows None (passed as NULL)
    """
    base = ndpointer(*args, **kwargs)

    def from_param(cls, obj):
        if obj is None:
            return obj
        return base.from_param(obj)

    return type(base.__name__, (base,), {"from_param": classmethod(from_param)})


nullable_double_array = wrapped_ndptr(dtype=ctypes.c_double, flags=("C_CONTIGUOUS"))

err_ptr = ctypes.POINTER(ctypes.c_void_p)

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

FIXED_SAMPLER_VARIABLES = [
    "lp__",
    "accept_stat__",
]


class HMCMetric(Enum):
    UNIT = 0
    DENSE = 1
    DIAG = 2


class OptimizationAlgorithm(Enum):
    NEWTON = 0
    BFGS = 1
    LBFGS = 2


# also allow inits from a StanOutput
def encode_stan_json(data: Union[str, Dict[str, Any]]) -> bytes:
    """Turn the provided data into something we can send to C++."""
    if isinstance(data, str):
        return data.encode()
    return dump_stan_json(data).encode()


class FFIStanModel:
    def __init__(self, model):
        if model.endswith(".stan"):
            libname = model[:-5] + "_model.so"
            subprocess.run(["make", libname])
            self._lib = ctypes.CDLL(libname)
        else:
            self._lib = ctypes.CDLL(model)

        self._create_model = self._lib.ffistan_create_model
        self._create_model.restype = ctypes.c_void_p
        self._create_model.argtypes = [ctypes.c_char_p, ctypes.c_uint, err_ptr]

        self._delete_model = self._lib.ffistan_destroy_model
        self._delete_model.restype = None
        self._delete_model.argtypes = [ctypes.c_void_p]

        self._get_names = self._lib.ffistan_model_param_names
        self._get_names.restype = ctypes.c_char_p
        self._get_names.argtypes = [ctypes.c_void_p]

        self._get_free_params = self._lib.ffistan_model_num_free_params
        self._get_free_params.restype = ctypes.c_size_t
        self._get_free_params.argtypes = [ctypes.c_void_p]

        self._ffi_sample = self._lib.ffistan_sample
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
            nullable_double_array,  # metric out
            err_ptr,
        ]

        self._ffi_pathfinder = self._lib.ffistan_pathfinder
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
            ctypes.c_int,  # refresh
            ctypes.c_int,  # num_threads
            double_array,  # output samples
            err_ptr,
        ]

        self._ffi_optimize = self._lib.ffistan_optimize
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
            err_ptr,
        ]

        self._get_error = self._lib.ffistan_get_error_message
        self._get_error.restype = ctypes.c_char_p
        self._get_error.argtypes = [ctypes.c_void_p]
        self._free_error = self._lib.ffistan_free_stan_error
        self._free_error.restype = None
        self._free_error.argtypes = [ctypes.c_void_p]
        get_separator = self._lib.ffistan_separator_char
        get_separator.restype = ctypes.c_char
        get_separator.argtypes = []
        self.sep = get_separator()

    def _raise_for_error(self, rc: int, err):
        if rc != 0:
            if err.contents:
                msg = self._get_error(err.contents).decode("utf-8")
                self._free_error(err.contents)
                if msg == "Interrupted":
                    raise KeyboardInterrupt()
                raise RuntimeError(msg)
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
        comma_separated = self._get_names(model).decode("utf-8").strip()
        if comma_separated == "":
            return []
        return list(comma_separated.split(","))

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
        metric=HMCMetric.DIAG,
        output_metric=False,
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
        if save_warmup and num_warmup < 0:
            raise ValueError("num_warmup must be non-negative")
        if num_samples < 1:
            raise ValueError("num_samples must be at least 1")

        seed = seed or np.random.randint(2**32 - 1)

        with self._get_model(data, seed) as model:
            model_params = self._get_free_params(model)
            if model_params == 0:
                raise ValueError("Model has no parameters to sample.")

            param_names = HMC_SAMPLER_VARIABLES + self._get_parameter_names(model)

            num_params = len(param_names)
            num_draws = num_samples + num_warmup * save_warmup
            out = np.zeros((num_chains, num_draws, num_params), dtype=np.float64)

            if output_metric:
                metric_size = (
                    (model_params, model_params)
                    if metric == HMCMetric.DENSE
                    else (model_params,)
                )
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
                metric_out,
                err,
            )
            self._raise_for_error(rc, err)

        output = StanOutput(param_names, out)
        if output_metric:
            return output, metric_out
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
        refresh=0,
        num_threads=-1,
    ):
        if num_draws < 1:
            raise ValueError("num_draws must be at least 1")

        seed = seed or np.random.randint(2**32 - 1)

        with self._get_model(data, seed) as model:
            param_names = PATHFINDER_VARIABLES + self._get_parameter_names(model)

            num_params = len(param_names)
            out = np.zeros((num_draws, num_params), dtype=np.float64)

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
                refresh,
                num_threads,
                out,
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
        seed = seed or np.random.randint(2**32 - 1)

        if isinstance(init, StanOutput):
            init = init.create_inits(chains=1, seed=seed)

        with self._get_model(data, seed) as model:
            param_names = OPTIMIZE_VARIABLES + self._get_parameter_names(model)

            num_params = len(param_names)
            out = np.zeros(num_params, dtype=np.float64)

            err = ctypes.pointer(ctypes.c_void_p())
            rc = self._ffi_optimize(
                model,
                encode_stan_json(init) if init is not None else None,
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
                err,
            )
            self._raise_for_error(rc, err)

        return StanOutput(param_names, out)
