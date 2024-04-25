### Generic function `optimizer`

```r
#### S3 method for class 'tinystan_model'
optimizer(
  model,
  data = "",
  init = NULL,
  seed = NULL,
  id = 1,
  init_radius = 2,
  algorithm = OptimizationAlgorithm$LBFGS,
  jacobian = FALSE,
  num_iterations = 2000,
  max_history_size = 5,
  init_alpha = 0.001,
  tol_obj = 1e-12,
  tol_rel_obj = 10000,
  tol_grad = 1e-08,
  tol_rel_grad = 1e+07,
  tol_param = 1e-08,
  refresh = 0,
  num_threads = -1
)
```

Run Stan's Optimization algorithms
