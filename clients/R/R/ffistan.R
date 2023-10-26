HMCMetric <- list(UNIT = 0, DENSE = 1, DIAG = 2)

HMC_SAMPLER_VARIABLES = c("lp__", "accept_stat__", "stepsize__", "treedepth__", "n_leapfrog__",
    "divergent__", "energy__")

PATHFINDER_VARIABLES = c("lp_approx__", "lp__")

OptimizationAlgorithm <- list(NEWTON = 0, BFGS = 1, LBFGS = 2)

OPTIMIZATION_VARIABLES = c("lp__")

FFIStanModel <- R6::R6Class("FFIStanModel", public = list(initialize = function(lib) {
    if (.Platform$OS.type == "windows") {
        lib_old <- lib
        lib <- paste0(tools::file_path_sans_ext(lib), ".dll")
        file.copy(from = lib_old, to = lib)
    }

    private$lib <- tools::file_path_as_absolute(lib)
    private$lib_name <- tools::file_path_sans_ext(basename(lib))
    if (is.loaded("ffistan_create_model_R", PACKAGE = private$lib_name)) {
        warning(paste0("Loading a shared object '", lib, "' which is already loaded.\n",
            "If the file has changed since the last time it was loaded, this load may not update the library!"))
    }

    dyn.load(private$lib, PACKAGE = private$lib_name)

    sep <- .C("ffistan_separator_char_R", sep = raw(1), PACKAGE = private$lib_name)$sep
    private$sep <- rawToChar(sep)

}, sample = function(data = "", num_chains = 4, inits = NULL, seed = NULL, id = 1,
    init_radius = 2, num_warmup = 1000, num_samples = 1000, metric = HMCMetric$DIAG,
    save_metric = FALSE, adapt = TRUE, delta = 0.8, gamma = 0.05, kappa = 0.75, t0 = 10,
    init_buffer = 75, term_buffer = 50, window = 25, save_warmup = FALSE, stepsize = 1,
    stepsize_jitter = 0, max_depth = 10, refresh = 0, num_threads = -1) {

    if (num_chains < 1) {
        stop("num_chains must be at least 1")
    }
    if (save_warmup && num_warmup < 0) {
        stop("num_warmup must be non-negative")
    }
    if (num_samples < 1) {
        stop("num_samples must be at least 1")
    }

    if (is.null(seed)) {
        seed <- as.integer(runif(1, min = 0, max = (2^31)))
    }

    private$with_model(data, seed, {
        free_params <- private$get_free_params(model)
        if (free_params == 0) {
            stop("Model has no parameters to sample")
        }

        params <- c(HMC_SAMPLER_VARIABLES, private$get_parameter_names(model))
        num_params <- length(params)
        num_draws <- as.integer(save_warmup) * num_warmup + num_samples
        output_size <- num_params * num_chains * num_draws

        if (save_metric) {
            if (metric == HMCMetric$DENSE) {
                metric_out <- double(num_chains * free_params * free_params)
            } else {
                metric_out <- double(num_chains * free_params)
            }
        } else {
            metric_out <- as.raw(rep(0, 8))
        }

        vars <- .C("ffistan_sample_R", return_code = as.integer(0), as.raw(model),
            as.integer(num_chains), private$encode_inits(inits), as.integer(seed),
            as.integer(id), as.double(init_radius), as.integer(num_warmup), as.integer(num_samples),
            as.integer(metric), as.logical(adapt), as.double(delta), as.double(gamma),
            as.double(kappa), as.double(t0), as.integer(init_buffer), as.integer(term_buffer),
            as.integer(window), as.logical(save_warmup), as.double(stepsize), as.double(stepsize_jitter),
            as.integer(max_depth), as.integer(refresh), as.integer(num_threads),
            out = double(output_size), metric= metric_out, err = raw(8), PACKAGE = private$lib_name)
        handle_error(vars$return_code, private$lib_name, vars$err)
        # reshape the output matrix
        out <- aperm(array(vars$out, dim = c(num_params, num_draws, num_chains),
            dimnames = list(params, NULL, NULL)), c(3, 2, 1))

        if (save_metric){
            if (metric == HMCMetric$DENSE) {
                metric <- aperm(array(vars$metric, dim = c(free_params, free_params, num_chains)), c(3, 2, 1))
            } else {
                metric <- aperm(array(vars$metric, dim = c(free_params, num_chains)), c(2, 1))
            }
            return(list(params = params, draws = out, metric = metric))
        }

        list(params = params, draws = out)
    })
}, pathfinder = function(data = "", num_paths = 4, inits = NULL, seed = NULL, id = 1,
    init_radius = 2, num_draws = 1000, max_history_size = 5, init_alpha = 0.001,
    tol_obj = 1e-12, tol_rel_obj = 10000, tol_grad = 1e-08, tol_rel_grad = 1e+07,
    tol_param = 1e-08, num_iterations = 1000, num_elbo_draws = 100, num_multi_draws = 1000,
    refresh = 0, num_threads = -1) {
    if (num_draws < 1) {
        stop("num_draws must be at least 1")
    }

    if (is.null(seed)) {
        seed <- as.integer(runif(1, min = 0, max = (2^31)))
    }

    private$with_model(data, seed, {
        params <- c(PATHFINDER_VARIABLES, private$get_parameter_names(model))
        num_params <- length(params)
        output_size <- num_params * num_draws

        vars <- .C("ffistan_pathfinder_R", return_code = as.integer(0), as.raw(model),
            as.integer(num_paths), private$encode_inits(inits), as.integer(seed),
            as.integer(id), as.double(init_radius), as.integer(num_draws), as.integer(max_history_size),
            as.double(init_alpha), as.double(tol_obj), as.double(tol_rel_obj), as.double(tol_grad),
            as.double(tol_rel_grad), as.double(tol_param), as.integer(num_iterations),
            as.integer(num_elbo_draws), as.integer(num_multi_draws), as.integer(refresh),
            as.integer(num_threads), out = double(output_size), err = raw(8), PACKAGE = private$lib_name)
        handle_error(vars$return_code, private$lib_name, vars$err)
        # reshape the output matrix
        out <- t(array(vars$out, dim = c(num_params, num_draws), dimnames = list(params,
            NULL)))
        list(params = params, draws = out)
    })
}, optimize = function(data = "", init = NULL, seed = NULL, id = 1, init_radius = 2,
    algorithm = OptimizationAlgorithm$LBFGS, jacobian = FALSE, num_iterations = 2000,
    max_history_size = 5, init_alpha = 0.001, tol_obj = 1e-12, tol_rel_obj = 10000,
    tol_grad = 1e-08, tol_rel_grad = 1e+07, tol_param = 1e-08, refresh = 0, num_threads = -1) {

    if (is.null(seed)) {
        seed <- as.integer(runif(1, min = 0, max = (2^31)))
    }

    private$with_model(data, seed, {
        params <- c(OPTIMIZATION_VARIABLES, private$get_parameter_names(model))
        num_params <- length(params)
        output_size <- num_params

        vars <- .C("ffistan_optimize_R", return_code = as.integer(0), as.raw(model),
            private$encode_inits(init), as.integer(seed), as.integer(id), as.double(init_radius),
            as.integer(algorithm), as.integer(num_iterations), as.logical(jacobian),
            as.integer(max_history_size), as.double(init_alpha), as.double(tol_obj),
            as.double(tol_rel_obj), as.double(tol_grad), as.double(tol_rel_grad),
            as.double(tol_param), as.integer(refresh), as.integer(num_threads), out = double(output_size),
            err = raw(8), PACKAGE = private$lib_name)
        handle_error(vars$return_code, private$lib_name, vars$err)
        out <- array(vars$out, dim = c(num_params), dimnames = list(params))
        list(params = params, optimum = out)
    })

}), private = list(lib = NA, lib_name = NA, sep = NA, with_model = function(data,
    seed, block) {
    ffi_ret <- .C("ffistan_create_model_R", model = raw(8), as.character(data), as.integer(seed),
        err = raw(8), NAOK = TRUE, PACKAGE = private$lib_name)
    handle_error(all(ffi_ret$model == 0), private$lib_name, ffi_ret$err)
    tryCatch({
        # this is the equivalent of base R's `with` function
        eval(substitute(block), ffi_ret, enclos = parent.frame())
    }, finally = {
        .C("ffistan_destroy_model_R", as.raw(ffi_ret$model), PACKAGE = private$lib_name)
    })
}, get_parameter_names = function(model) {
    param_names_raw <- .C("ffistan_model_param_names_R", as.raw(model), names = as.character(""),
        PACKAGE = private$lib_name)$names
    if (param_names_raw == "") {
        return(c())
    }
    strsplit(param_names_raw, ",")[[1]]

}, get_free_params = function(model) {
    .C("ffistan_model_num_free_params_R", as.raw(model), params = as.integer(0),
        PACKAGE = private$lib_name)$params
}, encode_inits = function(inits) {
    if (is.null(inits)) {
        return(as.character(""))
    }
    if (is.character(inits)) {
        return(as.character(inits))
    }
    if (is.list(inits)) {
        return(as.character(paste0(inits, collapse = private$sep)))
    }
    stop("inits must be a character vector or a list")
}), cloneable = TRUE)

#' Get and free the error message stored at the C++ pointer
#' @keywords internal
handle_error <- function(rc, lib_name, err_ptr) {
    if (rc != 0) {
        if (all(err_ptr == 0)) {
            stop(paste("Unknown error, function returned code", rc))
        }
        msg <- .C("ffistan_get_error_message_R", as.raw(err_ptr), err_msg = as.character(""),
            PACKAGE = lib_name)$err_msg
        .C("ffistan_free_stan_error_R", as.raw(err_ptr), PACKAGE = lib_name)
        stop(msg)
    }
}

if (sys.nframe() == 0) {
    model <- FFIStanModel$new("./test_models/bernoulli/bernoulli_model.so")
    data <- "./test_models/bernoulli/bernoulli.data.json"

    fit <- model$sample(data, num_samples = 10000, num_chains = 10)
    print(colMeans(fit$draws, dims = 2)[8])

    pf = model$pathfinder(data)
    print(colMeans(pf$draws)[3])

    o = model$optimize(data)
    print(o$optimum[2])
}
