test_that("data arguments work", {

    out1 <- bernoulli_model$pathfinder(BERNOULLI_DATA)
    expect_true(mean(out1$theta) > 0.2 && mean(out1$theta) < 0.3)

    data_file <- file.path(stan_folder, "bernoulli", "bernoulli.data.json")
    out2 <- bernoulli_model$pathfinder(data = data_file)
    expect_true(mean(out2$theta) > 0.2 && mean(out2$theta) < 0.3)

})


test_that("output sizes are correct", {

    out1 <- bernoulli_model$pathfinder(BERNOULLI_DATA, num_paths = 4, num_draws = 101,
        num_multi_draws = 99)
    expect_equal(posterior::ndraws(out1), 99)

    out2 <- bernoulli_model$pathfinder(BERNOULLI_DATA, num_paths = 1, num_draws = 101,
        num_multi_draws = 103)
    expect_equal(posterior::ndraws(out2), 103)

    out3 <- bernoulli_model$pathfinder(BERNOULLI_DATA, num_paths = 2, num_draws = 105,
        num_multi_draws = 1, calculate_lp = FALSE)
    expect_equal(posterior::ndraws(out3), 2 * 105)

    out4 <- bernoulli_model$pathfinder(BERNOULLI_DATA, num_paths = 3, num_draws = 107,
        num_multi_draws = 1, psis_resample = FALSE)
    expect_equal(posterior::ndraws(out4), 3 * 107)

    out5 <- bernoulli_model$pathfinder(BERNOULLI_DATA, num_paths = 1, num_draws = 109,
        num_multi_draws = 1, psis_resample = FALSE)
    expect_equal(posterior::ndraws(out5), 109)
})

test_that("calculate_lp works", {
    out <- bernoulli_model$pathfinder(BERNOULLI_DATA, num_paths = 2, calculate_lp = FALSE)

    expect_gt(sum(is.nan(posterior::draws_of(out$lp__))), 0)
    expect_lt(sum(is.nan(posterior::draws_of(out$lp__))), 2000)

    out_single <- bernoulli_model$pathfinder(BERNOULLI_DATA, num_paths = 1, calculate_lp = FALSE)

    expect_gt(sum(is.nan(posterior::draws_of(out_single$lp__))), 0)
    expect_lt(sum(is.nan(posterior::draws_of(out_single$lp__))), 1000)
})

test_that("seed works", {

    out1 <- bernoulli_model$pathfinder(BERNOULLI_DATA, seed = 123)
    out2 <- bernoulli_model$pathfinder(BERNOULLI_DATA, seed = 123)

    expect_equal(out1$theta, out2$theta)

    out3 <- bernoulli_model$pathfinder(BERNOULLI_DATA, seed = 456)
    expect_error(expect_equal(out1$theta, out3$theta))

})
test_that("inits work", {

    init1 <- "{\"mu\": -1000}"
    out1 <- multimodal_model$pathfinder(inits = init1)
    expect_true(all(out1$mu < 0))

    init2 <- "{\"mu\": 1000}"
    out2 <- multimodal_model$pathfinder(inits = init2)
    expect_true(all(out2$mu > 0))

    temp_file <- tempfile(fileext = ".json")
    write(init1, temp_file)
    out3 <- multimodal_model$pathfinder(num_paths = 2, inits = c(temp_file, init1))
    expect_true(all(out3$mu < 0))
})


test_that("bad data handled properly", {

    data <- "{\"N\": -1}"
    expect_error(bernoulli_model$pathfinder(data), "greater than or equal to 0")

    data <- "{\"N\": 1, \"y\": [1,2]}"
    expect_error(bernoulli_model$pathfinder(data), "mismatch in dimension")

    expect_error(bernoulli_model$pathfinder("{\"bad\"}"), "Error in JSON parsing")

    expect_error(bernoulli_model$pathfinder("not/real/path.json"), "Could not open data file")

})

test_that("bad inits handled properly", {

    init <- "{\"theta\": 2}"
    expect_error(bernoulli_model$pathfinder(BERNOULLI_DATA, inits = init), "Initialization failed")

    expect_error(bernoulli_model$pathfinder(BERNOULLI_DATA, num_paths = 1, inits = init),
        "Initialization failed")

    expect_error(bernoulli_model$pathfinder(BERNOULLI_DATA, inits = "bad/path.json"),
        "Could not open data file")

    inits <- c(init, init)
    expect_error(bernoulli_model$pathfinder(BERNOULLI_DATA, num_paths = 2, inits = inits),
        "Initialization failed")

    init2 <- "{\"theta\": 0.2}"

    # unlike sample, a failure of subset of inits is not fatal
    inits <- rep(list(init), 10)
    inits[[11]] <- init2
    bernoulli_model$pathfinder(BERNOULLI_DATA, num_paths = 11, num_multi_draws = 10,
        inits = inits)

    inits <- list(init2, init2)
    expect_error(bernoulli_model$pathfinder(BERNOULLI_DATA, num_paths = 1, inits = inits),
        "match the number of chains")
    expect_error(bernoulli_model$pathfinder(BERNOULLI_DATA, num_paths = 3, inits = inits),
        "match the number of chains")

})

test_that("empty model ok", {
    expect_error(empty_model$pathfinder(), "no parameters")
})

test_that("bad args raise errors", {

    expect_error(bernoulli_model$pathfinder(BERNOULLI_DATA, num_paths = 0), "at least 1")
    expect_error(bernoulli_model$pathfinder(BERNOULLI_DATA, num_draws = 0), "at least 1")
    expect_error(bernoulli_model$pathfinder(BERNOULLI_DATA, id = 0), "positive")
    expect_error(bernoulli_model$pathfinder(BERNOULLI_DATA, init_radius = -0.1),
        "non-negative")
    expect_error(bernoulli_model$pathfinder(BERNOULLI_DATA, num_threads = 0), "positive")
    expect_error(bernoulli_model$pathfinder(BERNOULLI_DATA, num_iterations = 0),
        "positive")
    expect_error(bernoulli_model$pathfinder(BERNOULLI_DATA, num_elbo_draws = 0),
        "positive")
    expect_error(bernoulli_model$pathfinder(BERNOULLI_DATA, num_multi_draws = 0),
        "at least 1")

    expect_error(bernoulli_model$pathfinder(BERNOULLI_DATA, max_history_size = 0),
        "positive")
    expect_error(bernoulli_model$pathfinder(BERNOULLI_DATA, init_alpha = 0), "positive")
    expect_error(bernoulli_model$pathfinder(BERNOULLI_DATA, tol_obj = 0), "positive")
    expect_error(bernoulli_model$pathfinder(BERNOULLI_DATA, tol_rel_obj = 0), "positive")
    expect_error(bernoulli_model$pathfinder(BERNOULLI_DATA, tol_grad = 0), "positive")
    expect_error(bernoulli_model$pathfinder(BERNOULLI_DATA, tol_rel_grad = 0), "positive")
    expect_error(bernoulli_model$pathfinder(BERNOULLI_DATA, tol_param = 0), "positive")

})

