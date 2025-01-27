class TFTTimeSeriesModel(BaseTimeSeriesModel):
    """
    A time-series model using Darts' TemporalFusionTransformer (TFT).
    Optionally uses time-based features (exogenous variables) via create_time_features().
    """

    def __init__(self, use_hyperopt: bool = False, n_trials: int = 10):
        """
        Initialize the TFT model parameters.

        Args:
            use_hyperopt (bool): Whether to perform hyperparameter tuning.
            n_trials (int): Number of Optuna trials for tuning.
        """
        self.use_hyperopt = use_hyperopt
        self.n_trials = n_trials
        self.model = None  # Will store the trained TFT model
        self.target_scaler = None  # Scaler for target
        self.covariate_scaler = None  # Scaler for covariates
        self.best_params = None  # To store the best hyperparameters from tuning

    def _create_features(self, df: pd.DataFrame) -> (TimeSeries, TimeSeries):
        """
        Convert DataFrame to Darts TimeSeries and create past covariates.

        Args:
            df (pd.DataFrame): Input DataFrame with DateTime index and 'value' column.

        Returns:
            TimeSeries: Transformed target series.
            TimeSeries: Transformed past covariates.
        """
        # Convert target to TimeSeries
        ts = TimeSeries.from_dataframe(df, value_cols=["value"], freq=None)

        # Create covariates
        df_feat = create_time_features(df)
        cov_cols = ["hour_sin", "hour_cos", "dow_sin", "dow_cos"]
        covariates = TimeSeries.from_dataframe(df_feat[cov_cols], freq=None)

        return ts, covariates

    def _objective(self, trial, ts_train: TimeSeries, covariates_train: TimeSeries) -> float:
        """
        TODO: adapt to the interface objective() function
        Objective function for Optuna hyperparameter tuning.

        Args:
            trial: Optuna trial object.
            ts_train (TimeSeries): Training target series.
            covariates_train (TimeSeries): Training past covariates.

        Returns:
            float: Mean Squared Error of the backtest.
        """
        # Define hyperparameter search space
        hidden_size = trial.suggest_int("hidden_size", 16, 128, step=16)
        lstm_layers = trial.suggest_int("lstm_layers", 1, 4)
        dropout = trial.suggest_float("dropout", 0.0, 0.5)
        batch_size = trial.suggest_int("batch_size", 16, 64, step=16)

        # Instantiate the TFT model with current hyperparameters
        model = TFTModel(
            input_chunk_length=24,
            output_chunk_length=6,
            hidden_size=hidden_size,
            lstm_layers=lstm_layers,
            dropout=dropout,
            batch_size=batch_size,
            n_epochs=10,
            random_state=42,
        )

        try:
            # Fit the model
            model.fit(ts_train, past_covariates=covariates_train, verbose=False)

            # Perform backtest
            backtest = model.backtest(
                series=ts_train,
                past_covariates=covariates_train,
                start=0.8,  # use last 20% for validation
                forecast_horizon=6,
                stride=6,
                retrain=False
            )

            # Calculate MSE
            mse = mean_squared_error(
                ts_train.slice_intersect(backtest).values(),
                backtest.values()
            )

            return mse

        except Exception as e:
            # If model fitting fails, return a high MSE to discourage this parameter set
            return float('inf')

    def tune(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """
        Perform hyperparameter tuning using Optuna.

        Args:
            df (pd.DataFrame): Training DataFrame with DateTime index and 'value' column.
            **kwargs: Additional keyword arguments.

        Returns:
            Dict[str, Any]: The best hyperparameters found.
        """
        ts_train, covariates_train = self._create_features(df)

        # Scale target and covariates
        self.target_scaler = Scaler()
        self.covariate_scaler = Scaler()
        ts_train_scaled = self.target_scaler.fit_transform(ts_train)
        covariates_train_scaled = self.covariate_scaler.fit_transform(covariates_train)

        # Create Optuna study
        study = optuna.create_study(direction="minimize")
        study.optimize(
            lambda trial: self._objective(trial, ts_train_scaled, covariates_train_scaled),
            n_trials=self.n_trials
        )

        self.best_params = study.best_params
        return self.best_params

    def train(self, df: pd.DataFrame, **kwargs) -> None:
        """
        Train the TFT model using the best hyperparameters.

        Args:
            df (pd.DataFrame): Training DataFrame with DateTime index and 'value' column.
            **kwargs: Additional keyword arguments.
        """
        ts_train, covariates_train = self._create_features(df)

        # Scale target and covariates
        self.target_scaler = Scaler()
        self.covariate_scaler = Scaler()
        ts_train_scaled = self.target_scaler.fit_transform(ts_train)
        covariates_train_scaled = self.covariate_scaler.fit_transform(covariates_train)

        # Use best_params if available, else use defaults
        if self.use_hyperopt and self.best_params:
            hidden_size = self.best_params.get("hidden_size", 64)
            lstm_layers = self.best_params.get("lstm_layers", 1)
            dropout = self.best_params.get("dropout", 0.1)
            batch_size = self.best_params.get("batch_size", 32)
        else:
            hidden_size = 64
            lstm_layers = 1
            dropout = 0.1
            batch_size = 32

        # Instantiate the TFT model with selected hyperparameters
        self.model = TFTModel(
            input_chunk_length=24,
            output_chunk_length=6,
            hidden_size=hidden_size,
            lstm_layers=lstm_layers,
            dropout=dropout,
            batch_size=batch_size,
            n_epochs=10,
            random_state=42,
        )

        try:
            # Fit the model
            self.model.fit(ts_train_scaled, past_covariates=covariates_train_scaled, verbose=False)
        except Exception as e:
            print(f"Failed to train TFT model: {e}")
            self.model = None

    def evaluate(self, df: pd.DataFrame, **kwargs) -> float:
        """
        Evaluate the trained TFT model on the test set.

        Args:
            df (pd.DataFrame): Test DataFrame with DateTime index and 'value' column.
            **kwargs: Additional keyword arguments.

        Returns:
            float: Mean Squared Error of the predictions.
        """
        if self.model is None:
            raise ValueError("Model has not been trained. Call train() first.")

        ts_test, covariates_test = self._create_features(df)

        # Scale test data using the same scalers
        ts_test_scaled = self.target_scaler.transform(ts_test)
        covariates_test_scaled = self.covariate_scaler.transform(covariates_test)

        try:
            # Predict
            preds = self.model.predict(
                n=len(ts_test_scaled),
                series=ts_test_scaled,
                past_covariates=covariates_test_scaled
            )

            # Compute MSE
            mse = mean_squared_error(ts_test_scaled.values(), preds.values())

            return mse

        except Exception as e:
            print(f"Failed to predict using TFT model: {e}")
            return float('inf')
