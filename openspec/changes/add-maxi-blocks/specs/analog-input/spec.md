# Spec Delta

## ADDED Requirements

### Requirement: Moving average restart
An experiment program or another block SHALL be able to restart the moving average from ST. After a restart, `Status.ValueFiltered` SHALL be computed only from values received in later calls. `Cfg.FilterSize` and the scaling SHALL NOT change.

#### Scenario: Restart after a step
- **WHEN** the input has been constant at 1.0 V for more than `Cfg.FilterSize` cycles, the average is restarted, and the input is constant at 3.0 V from the next call on
- **THEN** `Status.ValueFiltered` is 3.0 V from the next call on
