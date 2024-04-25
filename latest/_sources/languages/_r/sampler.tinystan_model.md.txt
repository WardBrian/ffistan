### Generic function `sampler`

```r
#### S3 method for class 'tinystan_model'
sampler(
  model,
  data = "",
  num_chains = 4,
  inits = NULL,
  seed = NULL,
  id = 1,
  init_radius = 2,
  num_warmup = 1000,
  num_samples = 1000,
  metric = HMCMetric$DIAGONAL,
  init_inv_metric = NULL,
  save_metric = FALSE,
  adapt = TRUE,
  delta = 0.8,
  gamma = 0.05,
  kappa = 0.75,
  t0 = 10,
  init_buffer = 75,
  term_buffer = 50,
  window = 25,
  save_warmup = FALSE,
  stepsize = 1,
  stepsize_jitter = 0,
  max_depth = 10,
  refresh = 0,
  num_threads = -1
)
```

Run Stan's NUTS sampler

#### Examples

```r
data_file <- system.file('bernoulli.data.json', package = 'tinystan')
mod <- tinystan_model(system.file('bernoulli.stan', package = 'tinystan'))
fit = sampler(model = mod, data = data_file)
fit
```
