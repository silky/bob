#include "machine/Gaussian.h"
#include <cfloat>

double Torch::machine::Log::LogAdd(double log_a, double log_b) {
  double minusdif;
  
  if (log_a < log_b)
  {
    double tmp = log_a;
    log_a = log_b;
    log_b = tmp;
  }
  
  minusdif = log_b - log_a;
  //#ifdef DEBUG
  if (std::isnan(minusdif))
  printf("LogAdd: minusdif (%f) log_b (%f) or log_a (%f) is nan\n", minusdif, log_b, log_a);
  //#endif
  if (minusdif < MINUS_LOG_THRESHOLD) return log_a;
  else return log_a + log1p(exp(minusdif));
}

double Torch::machine::Log::LogSub(double log_a, double log_b) {
  double minusdif;
  
  if (log_a < log_b)
    printf("LogSub: log_a (%f) should be greater than log_b (%f)", log_a, log_b);
  
  minusdif = log_b - log_a;
  //#ifdef DEBUG
  if (std::isnan(minusdif))
    printf("LogSub: minusdif (%f) log_b (%f) or log_a (%f) is nan", minusdif, log_b, log_a);
  //#endif
  if (log_a == log_b) return LogZero;
  else if (minusdif < MINUS_LOG_THRESHOLD) return log_a;
  else return log_a + log1p(-exp(minusdif));
}



/// Default constructor
Torch::machine::Gaussian::Gaussian() {
  resize(0);
}

/// Constructor
/// @param[in] n_inputs The feature dimensionality
Torch::machine::Gaussian::Gaussian(int n_inputs) {
  resize(n_inputs);
}

/// Destructor
Torch::machine::Gaussian::~Gaussian() {
}

Torch::machine::Gaussian::Gaussian(const Gaussian& other) {
  copy(other);
}

Torch::machine::Gaussian& Torch::machine::Gaussian::operator= (const Gaussian &other) {
  if (this != &other) {
    copy(other);
  }

  return *this;
}


void Torch::machine::Gaussian::copy(const Gaussian& other) {
  m_n_inputs = other.m_n_inputs;
  
  m_mean.resize(m_n_inputs);
  m_mean = other.m_mean;
  
  m_variance.resize(m_n_inputs);
  m_variance = other.m_variance;
  
  m_variance_thresholds.resize(m_n_inputs);
  m_variance_thresholds = other.m_variance_thresholds;

  g_norm = other.g_norm;
}

/// Set the feature dimensionality
/// Overrides Machine::setNInputs
void Torch::machine::Gaussian::setNInputs(int n_inputs) {
  resize(n_inputs);
}

/// Set the input dimensionality, reset the mean to zero
/// and the variance to one.
/// @param n_inputs The feature dimensionality
bool Torch::machine::Gaussian::resize(int n_inputs) {
  m_n_inputs = n_inputs;
  m_mean.resize(m_n_inputs);
  m_mean = 0;
  m_variance.resize(m_n_inputs);
  m_variance = 1;
  m_variance_thresholds.resize(m_n_inputs);
  m_variance_thresholds = 0;

  // Re-compute g_norm, because m_n_inputs and m_variance
  // have changed
  preComputeConstants();
  return true;
}

/// Set the mean
bool Torch::machine::Gaussian::setMean(const blitz::Array<double,1> &mean) {
  m_mean = mean;
  return true;
}

/// Set the variance
bool Torch::machine::Gaussian::setVariance(const blitz::Array<double,1> &variance) {

  m_variance = variance;

  // Apply variance flooring threshold
  blitz::Array<bool,1> isTooSmall(m_n_inputs);
  isTooSmall = m_variance < m_variance_thresholds;
  m_variance += (m_variance_thresholds - m_variance) * isTooSmall;
  
  // Re-compute g_norm, because m_variance has changed
  preComputeConstants();

  return true;
}

bool Torch::machine::Gaussian::setVarianceThresholds(const blitz::Array<double,1> &variance_thresholds) {
  m_variance_thresholds = variance_thresholds;
  
  // setVariance() will reset the variances that are now too small
  setVariance(m_variance);
  return true;
}

bool Torch::machine::Gaussian::setVarianceThresholds(double factor) {
  blitz::Array<double,1> variance_thresholds(m_n_inputs);
  variance_thresholds = m_variance * factor;
  setVarianceThresholds(variance_thresholds);
  return true;
}

/// Output the log likelihood of the sample, x 
/// @param x The data sample (feature vector)
double Torch::machine::Gaussian::logLikelihood(const blitz::Array<float,1> &x) const {
  double z = blitz::sum(blitz::pow2(x - m_mean) / m_variance);
  double logLikelihood = (-0.5 * (g_norm + z));
  return logLikelihood;
}

/// Output the logLikelihood of the sample, x 
/// (overrides Machine::forward)
double Torch::machine::Gaussian::forward(const blitz::Array<float,1> &input) const {
  return logLikelihood(input);
}

/// Get the variance flooring thresholds
bool Torch::machine::Gaussian::getVarianceThresholds(blitz::Array<double,1> &variance_thresholds) const {
  variance_thresholds.resize(m_n_inputs);
  variance_thresholds = m_variance_thresholds;
  return true;
}

/// Get the mean
bool Torch::machine::Gaussian::getMean(blitz::Array<double,1> &mean) const {
  mean.resize(m_n_inputs);
  mean = m_mean;
  return true;
}

/// Get the variance (the diagonal of the covariance matrix)
bool Torch::machine::Gaussian::getVariance(blitz::Array<double,1> &variance) const {
  variance.resize(m_n_inputs);
  variance = m_variance;
  return true;
}

/// Print the mean and variance of the Gaussian
bool Torch::machine::Gaussian::print() const {
  //Torch::core::info << "Mean = " << m_mean << std::endl;
  //Torch::core::info << "Variance = " << m_variance << std::endl;
  std::cout  << "Mean = " << m_mean << std::endl;
  std::cout << "Variance = " << m_variance << std::endl;
  return true;
}

/// Compute and store the value of g_norm, 
/// to later speed up evaluation of logLikelihood()
/// Note: g_norm is defined as follows:
/// log(Gaussian pdf) = log(1/((2pi)^(k/2)(det)^(1/2)) * exp(...))
///                   = -1/2 * g_norm * (...)
bool Torch::machine::Gaussian::preComputeConstants() {
  double c = m_n_inputs * Log::Log2Pi;
  double log_det = 0.0;
  for(int i=0; i < m_n_inputs; ++i) {
    log_det += log(m_variance(i));
  }
  g_norm = c + log_det;
  return true;
}
