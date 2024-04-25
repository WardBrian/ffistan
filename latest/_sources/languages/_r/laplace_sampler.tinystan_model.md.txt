### Generic function `laplace_sampler`

```r
#### S3 method for class 'tinystan_model'
laplace_sampler(
  model,
  mode,
  data = "",
  num_draws = 1000,
  jacobian = TRUE,
  calculate_lp = TRUE,
  save_hessian = FALSE,
  seed = NULL,
  refresh = 0,
  num_threads = -1
)
```

Run Stan's Laplace approximation algorithm
