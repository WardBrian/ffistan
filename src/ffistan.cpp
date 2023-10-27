#include <stan/callbacks/logger.hpp>
#include <stan/callbacks/writer.hpp>
#include <stan/callbacks/structured_writer.hpp>
#include <stan/model/model_base.hpp>
#include <stan/services/util/create_rng.hpp>
#include <stan/services/pathfinder/multi.hpp>
#include <stan/services/pathfinder/single.hpp>
#include <stan/services/optimize/bfgs.hpp>
#include <stan/services/optimize/lbfgs.hpp>
#include <stan/services/optimize/newton.hpp>
#include <stan/services/sample/hmc_nuts_diag_e.hpp>
#include <stan/services/sample/hmc_nuts_diag_e_adapt.hpp>
#include <stan/services/sample/hmc_nuts_dense_e.hpp>
#include <stan/services/sample/hmc_nuts_dense_e_adapt.hpp>
#include <stan/services/sample/hmc_nuts_unit_e.hpp>
#include <stan/services/sample/hmc_nuts_unit_e_adapt.hpp>

#include <stan/math/prim/core/init_threadpool_tbb.hpp>

#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

#include "ffistan.h"
#include "errors.hpp"
#include "util.hpp"
#include "model.hpp"
#include "version.hpp"

#include "R_shims.cpp"

extern "C" {

FFIStanModel *ffistan_create_model(const char *data, unsigned int seed,
                                   stan_error **err) {
  try {
    return new FFIStanModel(data, seed);
  } catch (const std::exception &e) {
    if (err != nullptr) {
      *err = new stan_error(strdup(e.what()));
    }
  } catch (...) {
    if (err != nullptr) {
      *err = new stan_error(strdup("Unknown error"));
    }
  }
  return nullptr;
}

void ffistan_destroy_model(FFIStanModel *model) { delete model; }

const char *ffistan_model_param_names(const FFIStanModel *model) {
  return model->param_names;
}

size_t ffistan_model_num_free_params(const FFIStanModel *model) {
  return model->num_free_params;
}

int ffistan_sample(const FFIStanModel *ffimodel, size_t num_chains,
                   const char *inits, unsigned int seed, unsigned int id,
                   double init_radius, int num_warmup, int num_samples,
                   FFIStanMetric metric_choice,
                   /* adaptation params */ bool adapt, double delta,
                   double gamma, double kappa, double t0,
                   unsigned int init_buffer, unsigned int term_buffer,
                   unsigned int window, bool save_warmup, double stepsize,
                   double stepsize_jitter, int max_depth,
                   /* currently has no effect */ int refresh, int num_threads,
                   double *out, double *metric_out, stan_error **err) {
  try {
    check_positive("num_chains", num_chains);
    check_positive("id", id);
    check_nonnegative("init_radius", init_radius);
    check_nonnegative("num_warmup", num_warmup);
    check_positive("num_samples", num_samples);
    if (adapt) {
      check_between("delta", delta, 0, 1);
      check_positive("gamma", gamma);
      check_positive("kappa", kappa);
      check_positive("t0", t0);
    }
    check_nonnegative("init_buffer", init_buffer);
    check_nonnegative("term_buffer", term_buffer);
    check_nonnegative("window", window);
    check_positive("stepsize", stepsize);
    check_between("stepsize_jitter", stepsize_jitter, 0, 1);
    check_positive("max_depth", max_depth);

    init_threading(num_threads);

    auto json_inits = load_inits(num_chains, inits);

    auto &model = *ffimodel->model;

    // all HMC has 7 algorithm params
    int num_params = ffimodel->num_params + 7;
    int draws_offset = num_params * (num_samples + num_warmup * save_warmup);

    std::vector<buffer_writer> sample_writers;
    sample_writers.reserve(num_chains);
    for (size_t i = 0; i < num_chains; ++i) {
      sample_writers.emplace_back(out + draws_offset * i);
    }

    std::vector<metric_buffer_writer> metric_writers;
    metric_writers.reserve(num_chains);
    int num_model_params = ffimodel->num_free_params;
    int metric_offset = metric_choice == dense
                            ? num_model_params * num_model_params
                            : num_model_params;
    for (size_t i = 0; i < num_chains; ++i) {
      if (metric_out != nullptr)
        metric_writers.emplace_back(metric_out + metric_offset * i);
      else
        metric_writers.emplace_back(nullptr);
    }

    error_logger logger;
    ffistan_interrupt_handler interrupt;

    std::vector<stan::callbacks::writer> null_writers(num_chains);

    int return_code = 0;

    int thin = 1;  // no thinning

    switch (metric_choice) {
      case unit:
        if (adapt) {
          return_code = stan::services::sample::hmc_nuts_unit_e_adapt(
              model, num_chains, json_inits, seed, id, init_radius, num_warmup,
              num_samples, thin, save_warmup, refresh, stepsize,
              stepsize_jitter, max_depth, delta, gamma, kappa, t0, interrupt,
              logger, null_writers, sample_writers, null_writers,
              metric_writers);
        } else {
          return_code = stan::services::sample::hmc_nuts_unit_e(
              model, num_chains, json_inits, seed, id, init_radius, num_warmup,
              num_samples, thin, save_warmup, refresh, stepsize,
              stepsize_jitter, max_depth, interrupt, logger, null_writers,
              sample_writers, null_writers);
        }
        break;
      case dense:
        if (adapt) {
          return_code = stan::services::sample::hmc_nuts_dense_e_adapt(
              model, num_chains, json_inits, seed, id, init_radius, num_warmup,
              num_samples, thin, save_warmup, refresh, stepsize,
              stepsize_jitter, max_depth, delta, gamma, kappa, t0, init_buffer,
              term_buffer, window, interrupt, logger, null_writers,
              sample_writers, null_writers, metric_writers);
        } else {
          return_code = stan::services::sample::hmc_nuts_dense_e(
              model, num_chains, json_inits, seed, id, init_radius, num_warmup,
              num_samples, thin, save_warmup, refresh, stepsize,
              stepsize_jitter, max_depth, interrupt, logger, null_writers,
              sample_writers, null_writers);
        }
        break;
      case diagonal:
        if (adapt) {
          return_code = stan::services::sample::hmc_nuts_diag_e_adapt(
              model, num_chains, json_inits, seed, id, init_radius, num_warmup,
              num_samples, thin, save_warmup, refresh, stepsize,
              stepsize_jitter, max_depth, delta, gamma, kappa, t0, init_buffer,
              term_buffer, window, interrupt, logger, null_writers,
              sample_writers, null_writers, metric_writers);
        } else {
          return_code = stan::services::sample::hmc_nuts_diag_e(
              model, num_chains, json_inits, seed, id, init_radius, num_warmup,
              num_samples, thin, save_warmup, refresh, stepsize,
              stepsize_jitter, max_depth, interrupt, logger, null_writers,
              sample_writers, null_writers);
        }
        break;
    }
    if (return_code != 0) {
      if (err != nullptr) {
        *err = logger.get_error();
      }
    }

    return return_code;

  } catch (const std::exception &e) {
    if (err != nullptr) {
      *err = new stan_error(strdup(e.what()));
    }
  } catch (...) {
    if (err != nullptr) {
      *err = new stan_error(strdup("Unknown error"));
    }
  }
  return -1;
}

int ffistan_pathfinder(const FFIStanModel *ffimodel, size_t num_paths,
                       const char *inits, unsigned int seed, unsigned int id,
                       double init_radius, int num_draws,
                       /* tuning params */ int max_history_size,
                       double init_alpha, double tol_obj, double tol_rel_obj,
                       double tol_grad, double tol_rel_grad, double tol_param,
                       int num_iterations, int num_elbo_draws,
                       int num_multi_draws, int refresh, int num_threads,
                       double *out, stan_error **err) {
  try {
    // argument validation
    check_positive("num_paths", num_paths);
    check_positive("num_draws", num_draws);
    check_positive("id", id);
    check_nonnegative("init_radius", init_radius);
    check_positive("max_history_size", max_history_size);
    check_positive("init_alpha", init_alpha);
    check_positive("tol_obj", tol_obj);
    check_positive("tol_rel_obj", tol_rel_obj);
    check_positive("tol_grad", tol_grad);
    check_positive("tol_rel_grad", tol_rel_grad);
    check_positive("tol_param", tol_param);
    check_positive("num_iterations", num_iterations);
    check_positive("num_elbo_draws", num_elbo_draws);
    check_positive("num_multi_draws", num_multi_draws);

    init_threading(num_threads);

    auto json_inits = load_inits(num_paths, inits);

    auto &model = *ffimodel->model;

    buffer_writer pathfinder_writer(out);
    error_logger logger;

    ffistan_interrupt_handler interrupt;
    stan::callbacks::structured_writer dummy_json_writer;
    std::vector<stan::callbacks::writer> null_writers(num_paths);
    std::vector<stan::callbacks::structured_writer> null_structured_writers(
        num_paths);

    bool save_iterations = false;

    int return_code = 0;

    if (num_paths == 1) {
      return_code = stan::services::pathfinder::pathfinder_lbfgs_single(
          model, *(json_inits[0]), seed, id, init_radius, max_history_size,
          init_alpha, tol_obj, tol_rel_obj, tol_grad, tol_rel_grad, tol_param,
          num_iterations, num_elbo_draws, num_draws, save_iterations, refresh,
          interrupt, logger, null_writers[0], pathfinder_writer,
          null_structured_writers[0]);
    } else {
      return_code = stan::services::pathfinder::pathfinder_lbfgs_multi(
          model, json_inits, seed, id, init_radius, max_history_size,
          init_alpha, tol_obj, tol_rel_obj, tol_grad, tol_rel_grad, tol_param,
          num_iterations, num_elbo_draws, num_draws, num_multi_draws, num_paths,
          save_iterations, refresh, interrupt, logger, null_writers,
          null_writers, null_structured_writers, pathfinder_writer,
          dummy_json_writer);
    }

    if (return_code != 0) {
      if (err != nullptr) {
        *err = logger.get_error();
      }
    }

    return return_code;

  } catch (const std::exception &e) {
    if (err != nullptr) {
      *err = new stan_error(strdup(e.what()));
    }
  } catch (...) {
    if (err != nullptr) {
      *err = new stan_error(strdup("Unknown error"));
    }
  }
  return -1;
}

int ffistan_optimize(const FFIStanModel *ffimodel, const char *init,
                     unsigned int seed, unsigned int id, double init_radius,
                     FFIStanOptimizationAlgorithm algorithm, int num_iterations,
                     bool jacobian,
                     /* tuning params */ int max_history_size,
                     double init_alpha, double tol_obj, double tol_rel_obj,
                     double tol_grad, double tol_rel_grad, double tol_param,
                     int refresh, int num_threads, double *out,
                     stan_error **err) {
  try {
    check_positive("id", id);
    check_positive("num_iterations", num_iterations);
    check_nonnegative("init_radius", init_radius);

    if (algorithm == lbfgs) {
      check_positive("max_history_size", max_history_size);
    }
    if (algorithm == bfgs || algorithm == lbfgs) {
      check_positive("init_alpha", init_alpha);
      check_positive("tol_obj", tol_obj);
      check_positive("tol_rel_obj", tol_rel_obj);
      check_positive("tol_grad", tol_grad);
      check_positive("tol_rel_grad", tol_rel_grad);
      check_positive("tol_param", tol_param);
    }

    init_threading(num_threads);

    auto json_init = load_data(init);
    auto &model = *ffimodel->model;
    buffer_writer sample_writer(out);
    error_logger logger;

    ffistan_interrupt_handler interrupt;
    stan::callbacks::writer null_writer;

    bool save_iterations = false;

    int return_code = 0;
    switch (algorithm) {
      case newton:
        if (jacobian)
          return_code
              = stan::services::optimize::newton<stan::model::model_base, true>(
                  model, *json_init, seed, id, init_radius, num_iterations,
                  save_iterations, interrupt, logger, null_writer,
                  sample_writer);
        else
          return_code
              = stan::services::optimize::newton<stan::model::model_base,
                                                 false>(
                  model, *json_init, seed, id, init_radius, num_iterations,
                  save_iterations, interrupt, logger, null_writer,
                  sample_writer);
        break;
      case bfgs:
        if (jacobian)
          return_code
              = stan::services::optimize::bfgs<stan::model::model_base, true>(
                  model, *json_init, seed, id, init_radius, init_alpha, tol_obj,
                  tol_rel_obj, tol_grad, tol_rel_grad, tol_param,
                  num_iterations, save_iterations, refresh, interrupt, logger,
                  null_writer, sample_writer);
        else
          return_code
              = stan::services::optimize::bfgs<stan::model::model_base, false>(
                  model, *json_init, seed, id, init_radius, init_alpha, tol_obj,
                  tol_rel_obj, tol_grad, tol_rel_grad, tol_param,
                  num_iterations, save_iterations, refresh, interrupt, logger,
                  null_writer, sample_writer);
        break;
      case lbfgs:
        if (jacobian)
          return_code
              = stan::services::optimize::lbfgs<stan::model::model_base, true>(
                  model, *json_init, seed, id, init_radius, max_history_size,
                  init_alpha, tol_obj, tol_rel_obj, tol_grad, tol_rel_grad,
                  tol_param, num_iterations, save_iterations, refresh,
                  interrupt, logger, null_writer, sample_writer);
        else
          return_code
              = stan::services::optimize::lbfgs<stan::model::model_base, false>(
                  model, *json_init, seed, id, init_radius, max_history_size,
                  init_alpha, tol_obj, tol_rel_obj, tol_grad, tol_rel_grad,
                  tol_param, num_iterations, save_iterations, refresh,
                  interrupt, logger, null_writer, sample_writer);
        break;
    }

    if (return_code != 0) {
      if (err != nullptr) {
        *err = logger.get_error();
      }
    }

    return return_code;

  } catch (const std::exception &e) {
    if (err != nullptr) {
      *err = new stan_error(strdup(e.what()));
    }
  } catch (...) {
    if (err != nullptr) {
      *err = new stan_error(strdup("Unknown error"));
    }
  }
  return -1;
}

const char *ffistan_get_error_message(const stan_error *err) {
  if (err == nullptr) {
    return "Something went wrong: No error found";
  }
  return err->msg;
}

void ffistan_free_stan_error(stan_error *err) { delete (err); }

char ffistan_separator_char() { return SEPARATOR; }

int ffistan_major_version = FFISTAN_MAJOR;
int ffistan_minor_version = FFISTAN_MINOR;
int ffistan_patch_version = FFISTAN_PATCH;

void ffistan_version(int *major, int *minor, int *patch) {
  *major = ffistan_major_version;
  *minor = ffistan_minor_version;
  *patch = ffistan_patch_version;
}
}
