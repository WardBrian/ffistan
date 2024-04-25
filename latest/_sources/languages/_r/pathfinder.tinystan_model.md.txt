### Generic function `pathfinder`

```r
#### S3 method for class 'tinystan_model'
pathfinder(
  model,
  data = "",
  num_paths = 4,
  inits = NULL,
  seed = NULL,
  id = 1,
  init_radius = 2,
  num_draws = 1000,
  max_history_size = 5,
  init_alpha = 0.001,
  tol_obj = 1e-12,
  tol_rel_obj = 10000,
  tol_grad = 1e-08,
  tol_rel_grad = 1e+07,
  tol_param = 1e-08,
  num_iterations = 1000,
  num_elbo_draws = 25,
  num_multi_draws = 1000,
  calculate_lp = TRUE,
  psis_resample = TRUE,
  refresh = 0,
  num_threads = -1
)
```

Run Stan's pathfinder algorithm
