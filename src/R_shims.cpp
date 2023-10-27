#include "ffistan.h"

// R's .C function can only pass in pointers to C types, so we need to
// provide shims which indirect all our arguments and returns

extern "C" {
void ffistan_create_model_R(FFIStanModel** ptr_out, const char** data,
                            unsigned int* seed, stan_error** err) {
  *ptr_out = ffistan_create_model(*data, *seed, err);
}

void ffistan_destroy_model_R(FFIStanModel** model) {
  ffistan_destroy_model(*model);
}

void ffistan_model_param_names_R(FFIStanModel** model, char const** names) {
  *names = ffistan_model_param_names(*model);
}

void ffistan_model_num_free_params_R(FFIStanModel** model, int* n) {
  *n = ffistan_model_num_free_params(*model);
}

void ffistan_separator_char_R(char* sep) { *sep = ffistan_separator_char(); }

void ffistan_sample_R(int* return_code, FFIStanModel** model,
                      unsigned int* num_chains, char** inits,
                      unsigned int* seed, unsigned int* chain_id,
                      double* init_radius, int* num_warmup, int* num_samples,
                      int* metric_choice, int* adapt, double* delta,
                      double* gamma, double* kappa, double* t0,
                      unsigned int* init_buffer, unsigned int* term_buffer,
                      unsigned int* window, int* save_warmup, double* stepsize,
                      double* stepsize_jitter, int* max_depth, int* refresh,
                      int* num_threads, double* out, int* save_metric,
                      double* metric_out, stan_error** err) {
  //  difficult to directly pass a null pointer from R
  double* metric_out_ptr = nullptr;
  if (*save_metric)
    metric_out_ptr = metric_out;

  *return_code = ffistan_sample(
      *model, *num_chains, *inits, *seed, *chain_id, *init_radius, *num_warmup,
      *num_samples, static_cast<FFIStanMetric>(*metric_choice), (*adapt != 0),
      *delta, *gamma, *kappa, *t0, *init_buffer, *term_buffer, *window,
      (*save_warmup != 0), *stepsize, *stepsize_jitter, *max_depth, *refresh,
      *num_threads, out, metric_out, err);
}

void ffistan_pathfinder_R(
    int* return_code, FFIStanModel** model, unsigned int* num_paths,
    char** inits, unsigned int* seed, unsigned int* id, double* init_radius,
    int* num_draws, int* max_history_size, double* init_alpha, double* tol_obj,
    double* tol_rel_obj, double* tol_grad, double* tol_rel_grad,
    double* tol_param, int* num_iterations, int* num_elbo_draws,
    int* num_multi_draws, int* refresh, int* num_threads, double* out,
    stan_error** err) {
  *return_code = ffistan_pathfinder(
      *model, *num_paths, *inits, *seed, *id, *init_radius, *num_draws,
      *max_history_size, *init_alpha, *tol_obj, *tol_rel_obj, *tol_grad,
      *tol_rel_grad, *tol_param, *num_iterations, *num_elbo_draws,
      *num_multi_draws, *refresh, *num_threads, out, err);
}

void ffistan_optimize_R(int* return_code, FFIStanModel** ffimodel, char** init,
                        unsigned int* seed, unsigned int* id,
                        double* init_radius, int* algorithm,
                        int* num_iterations, int* jacobian,
                        int* max_history_size, double* init_alpha,
                        double* tol_obj, double* tol_rel_obj, double* tol_grad,
                        double* tol_rel_grad, double* tol_param, int* refresh,
                        int* num_threads, double* out, stan_error** err) {
  *return_code = ffistan_optimize(
      *ffimodel, *init, *seed, *id, *init_radius,
      static_cast<FFIStanOptimizationAlgorithm>(*algorithm), *num_iterations,
      *jacobian, *max_history_size, *init_alpha, *tol_obj, *tol_rel_obj,
      *tol_grad, *tol_rel_grad, *tol_param, *refresh, *num_threads, out, err);
}

void ffistan_get_error_message_R(stan_error** err, char const** err_msg) {
  *err_msg = ffistan_get_error_message(*err);
}

void ffistan_free_stan_error_R(stan_error** err) {
  ffistan_free_stan_error(*err);
}
}
