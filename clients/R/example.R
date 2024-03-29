library(tinystan)

model <- StanModel$new("../../test_models/bernoulli/bernoulli.stan")
data <- "../../test_models/bernoulli/bernoulli.data.json"

fit <- model$sample(data)
print(fit$theta)

pf <- model$pathfinder(data)
print(pf$theta)

o <- model$optimize(data)
print(o$theta)
