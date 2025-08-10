# RobustRunMetrics

## Description

RobustRunMetrics is a project aimed at developing and validating robust and personalized statistical models to estimate and predict key running performance metrics (such as critical speed, power, and estimated VO₂) using real-world Strava data. This project tackles the challenges of noisy and heterogeneous data typical of mobile applications, incorporating external variables like elevation and weather to improve prediction accuracy.

## Objectives

- Build a reproducible pipeline for cleaning, preprocessing, and standardizing Strava data.
- Implement and compare classical, robust, and Bayesian statistical models to estimate performance metrics.
- Develop predictive models for race times in common distances (10k, half marathon) based on training history.
- Integrate contextual variables (weather, elevation, time of day) to enhance predictions.
- Validate models with official race results and, if possible, lab data.

<pre markdown="1">
## Project Structure

```plaintext
RobustRunMetrics/
│
├── data/                   # Raw and processed data
├── notebooks/              # Jupyter notebooks for exploration and analysis
├── src/                    # Source code (pipeline, models, utilities)
├── results/                # Outputs, figures, and validation metrics
├── docs/                   # Additional documentation
├── requirements.txt        # Python dependencies
└── README.md               # Main documentation
```
</pre>


## Technologies and Libraries

- Python: pandas, numpy, scikit-learn, pymc, statsmodels, pyStrava
- R: brms, tidyverse, data.table, lubridate
- PostgreSQL for data storage
- Git for version control

## Getting Started

1. Clone the repository:
    ```
    git clone https://github.com/Ancamar/RobustRunMetrics.git
    ```
2. Install dependencies:
    ```
    pip install -r requirements.txt
    ```
3. Configure Strava API access (see `docs/STRAVA_API.md` for details).
4. Run notebooks in `notebooks/` for initial data exploration.
5. Follow the pipeline in `src/` for processing and modeling.

## Contributions

Contributions are welcome! Please open an issue to discuss major changes before submitting a pull request.
