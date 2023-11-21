
functions {
  vector sir(real t, vector y, real beta, real gamma, int N) {
    real S = y[1];
    real I = y[2];
    // real R = y[3];

    real dS_dt = - beta * I * S / N;
    real dI_dt = beta * I * S / N - gamma * I;
    real dR_dt = gamma * I;

    return [dS_dt, dI_dt, dR_dt]';
  }

}

data {
  int<lower=1> n_days;
  vector[3] y0;
  real t0;
  array[n_days] real ts;
  int N;
  array[n_days] int cases;
}

parameters {
  real<lower=0> gamma;
  real<lower=0> beta;
  real<lower=0> phi_inv;
}

transformed parameters {
  real phi = 1. / phi_inv;
  array[n_days] vector[3] y = ode_bdf(sir, y0, t0, ts, beta, gamma, N);
}

model {
  //priors
  beta ~ normal(2, 1);
  gamma ~ normal(0.4, 0.5);
  phi_inv ~ exponential(5);

  cases ~ neg_binomial_2(y[,2], phi);
  // cases ~ poisson(y[,2]);
}

generated quantities {
  real R0 = beta / gamma;
  real recovery_time = 1 / gamma;
  array[n_days] real pred_cases = neg_binomial_2_rng(y[,2], phi);
  // array[n_days] real pred_cases = poisson_rng(y[,2]);
}
