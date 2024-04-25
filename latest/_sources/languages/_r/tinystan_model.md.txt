### Class `tinystan_model`

```r
tinystan_model(lib, stanc_args = NULL, make_args = NULL, warn = TRUE)
```

Load a Stan model, compiling if necessary.

#### Examples

```r
data_file <- system.file('bernoulli.data.json', package = 'tinystan')
mod <- tinystan_model(system.file('bernoulli.stan', package = 'tinystan'))
fit = sampler(model = mod, data = data_file)
fit
```
