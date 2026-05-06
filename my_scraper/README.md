# PCSO Lottery Scraper and Analyzer

This project scrapes lottery results from the Philippine Charity Sweepstakes Office
(PCSO) website, saves them to JSON, and analyzes the historical draws with
Pandas, NumPy, Matplotlib, and Seaborn.

It can generate:

- scraped PCSO lottery results
- number frequency reports
- odd/even pattern analysis
- historical sum analysis
- Monte Carlo probability simulations
- data-informed possible number combinations for each lotto game
- CSV reports and PNG charts

Important: lottery draws are random. The suggested combinations are based on
historical patterns only. They are not guaranteed winning numbers.

## Project Files

- `pcso_lottery_scraper.py` - Scrapes live PCSO results and saves JSON data.
- `analyze_pcso_results.py` - Analyzes the scraped JSON and creates reports.
- `pcso_results.json` - Latest scraped lottery results.
- `analysis_outputs/` - Generated CSV reports and chart images.
- `requirements.txt` - Python dependencies.

## Requirements

- Python 3.8+
- Internet access for scraping live PCSO data
- pip

## Setup

From this folder:

```bash
cd /Users/jonasodones/Desktop/src/my_scraper
python3 -m venv pcso_env
./pcso_env/bin/python -m pip install -r requirements.txt
```

If `pcso_env` already exists, just install or update dependencies:

```bash
./pcso_env/bin/python -m pip install -r requirements.txt
```

## Scrape PCSO Results

Run:

```bash
./pcso_env/bin/python pcso_lottery_scraper.py
```

This creates or updates:

```text
pcso_results.json
```

The JSON output is a list of records:

```json
[
  {
    "lotto_game": "Ultra Lotto 6/58",
    "combinations": "01-58-25-43-26-16",
    "draw_date": "5/5/2026",
    "jackpot": "76,305,973.15",
    "winners": "10"
  }
]
```

The scraper exits with code `1` if the scrape fails or no lottery rows are
parsed. This makes it safer to use in scheduled jobs.

## Analyze Results

After `pcso_results.json` has data, run:

```bash
./pcso_env/bin/python analyze_pcso_results.py
```

By default, this analyzes all games and runs a Monte Carlo simulation for:

```text
Ultra Lotto 6/58
```

Generated files are saved in:

```text
analysis_outputs/
```

## Analysis Outputs

The analyzer creates these CSV files:

- `number_frequency_by_game.csv` - Frequency count for every number by game.
- `odd_even_patterns_by_game.csv` - Counts of patterns like `3 odd / 3 even`.
- `sum_statistics_by_game.csv` - Min, median, mean, max, and standard deviation of draw sums.
- `possible_winning_numbers_by_game.csv` - Data-informed suggested combinations for every game.
- `<game>_most_least_numbers.csv` - Most and least frequent numbers for the selected game.
- `<game>_monte_carlo.csv` - Monte Carlo checkpoints and hit counts.

The analyzer also creates PNG charts:

- `<game>_frequency.png`
- `<game>_odd_even_patterns.png`
- `<game>_sum_distribution.png`
- `<game>_monte_carlo_probability.png`

## Generate Possible Numbers

The analyzer automatically creates suggested combinations for each lotto game.

Default:

```bash
./pcso_env/bin/python analyze_pcso_results.py
```

Generate more suggestions per game:

```bash
./pcso_env/bin/python analyze_pcso_results.py --suggestions-per-game 5
```

The output is:

```text
analysis_outputs/possible_winning_numbers_by_game.csv
```

Each suggestion includes:

- lotto game
- suggested combination
- number sum
- odd/even pattern
- historical frequency score
- basis for the suggestion

The suggestions use:

- historical number frequency
- the most common odd/even pattern per game
- each game's median historical sum range
- game-specific number rules

## Monte Carlo Simulation

Run a simulation for a selected game:

```bash
./pcso_env/bin/python analyze_pcso_results.py --game "Ultra Lotto 6/58" --simulations 1000000
```

Examples:

```bash
./pcso_env/bin/python analyze_pcso_results.py --game "Grand Lotto 6/55" --simulations 1000000
./pcso_env/bin/python analyze_pcso_results.py --game "Megalotto 6/45" --simulations 1000000
./pcso_env/bin/python analyze_pcso_results.py --game "3D Lotto 9PM" --simulations 1000000
```

The simulation compares random generated draws against the latest known
combination for the selected game and reports:

- theoretical exact-match probability
- empirical simulation hit rate
- total hits across simulated draws

For large jackpot games, seeing `0` hits after one million simulations is normal
because the odds are extremely low.

## Useful Commands

Pretty-print the scraped JSON:

```bash
./pcso_env/bin/python -m json.tool pcso_results.json
```

Run scraper and then analysis:

```bash
./pcso_env/bin/python pcso_lottery_scraper.py
./pcso_env/bin/python analyze_pcso_results.py --simulations 1000000
```

Analyze a different selected game:

```bash
./pcso_env/bin/python analyze_pcso_results.py --game "Lotto 6/42"
```

Use a custom JSON input file:

```bash
./pcso_env/bin/python analyze_pcso_results.py --input my_results.json
```

Use a custom output folder:

```bash
./pcso_env/bin/python analyze_pcso_results.py --output-dir my_analysis
```

## Automated Pipeline

This project includes two automation scripts:

- `scripts/auto_pipeline.sh` - Bash implementation.
- `scripts/auto_pipeline.py` - Python implementation.

Both scripts run the same pipeline:

1. Acquire an exclusive lock so only one pipeline runs at a time.
2. Run the configured `synchronize` command.
3. Delete stale output:
   - remove `pcso_results.json`
   - delete files inside `analysis_outputs/`
   - keep the `analysis_outputs/` directory itself
4. Run `pcso_lottery_scraper.py`.
5. Wait until `pcso_results.json` exists and its file size is stable.
6. Run `analyze_pcso_results.py`.
7. Run `analyze_pcso_results.py --suggestions-per-game 5`.

Concurrency behavior: if another pipeline starts while analysis is running, the
new run waits for the current run to finish. This queues work and prevents
overlapping analysis processes from writing to the same output files.

### Run the Automated Pipeline

Bash version:

```bash
cd /Users/jonasodones/Desktop/src/my_scraper
SYNCHRONIZE_CMD=true ./scripts/auto_pipeline.sh
```

Python version:

```bash
cd /Users/jonasodones/Desktop/src/my_scraper
SYNCHRONIZE_CMD=true ./scripts/auto_pipeline.py
```

Use `SYNCHRONIZE_CMD=true` if your machine does not have a real command named
`synchronize`. If you do have a synchronization command, omit that override or
set it explicitly:

```bash
SYNCHRONIZE_CMD="synchronize" ./scripts/auto_pipeline.py
```

Logs are written to:

```text
logs/pipeline.log
```

The scripts also print logs to the terminal with timestamps and exit codes.

### Automation Configuration

You can configure the automation with environment variables:

```bash
export PROJECT_ROOT=/Users/jonasodones/Desktop/src/my_scraper
export VENV_PATH="$PROJECT_ROOT/pcso_env"
export PYTHON_BIN="$VENV_PATH/bin/python"
export SYNCHRONIZE_CMD="synchronize"
export FILE_POLL_INTERVAL=2
export STABILITY_SECONDS=5
export WAIT_TIMEOUT=600
export SCRAPER_CMD="$PYTHON_BIN pcso_lottery_scraper.py"
export PATH_TO_ANALYZER="$PROJECT_ROOT/analyze_pcso_results.py"
```

Common options:

- `PROJECT_ROOT` - Project directory. Default: repository root.
- `VENV_PATH` - Virtual environment path. Default: `pcso_env`.
- `PYTHON_BIN` - Python interpreter for the scraper/analyzer.
- `SYNCHRONIZE_CMD` - Command to run before cleanup and scraping.
- `SCRAPER_CMD` - Scraper command. Default: run `pcso_lottery_scraper.py`.
- `PATH_TO_ANALYZER` - Analyzer script path.
- `FILE_POLL_INTERVAL` - Seconds between file checks.
- `STABILITY_SECONDS` - Required stable file-size duration.
- `WAIT_TIMEOUT` - Max seconds to wait for `pcso_results.json`.
- `LOG_FILE` - Pipeline log path.

### Install Automation Dependencies

```bash
cd /Users/jonasodones/Desktop/src/my_scraper
python3 -m venv pcso_env
./pcso_env/bin/python -m pip install -r requirements.txt
chmod +x scripts/auto_pipeline.sh scripts/auto_pipeline.py
```

The Bash script uses `inotifywait` when available and falls back to polling.
On Debian or Ubuntu, install it with:

```bash
sudo apt-get install inotify-tools
```

Polling works even without `inotifywait`.

### Cron Example

Run the pipeline every day at 8:00 AM:

```cron
0 8 * * * cd /Users/jonasodones/Desktop/src/my_scraper && SYNCHRONIZE_CMD=true ./scripts/auto_pipeline.py >> logs/cron.log 2>&1
```

### Systemd Example

An example systemd unit is included:

```text
scripts/pcso-pipeline.service.example
```

Example Linux install using `/opt/pcso-lottery`:

```bash
sudo cp -R /Users/jonasodones/Desktop/src/my_scraper /opt/pcso-lottery
cd /opt/pcso-lottery
python3 -m venv pcso_env
./pcso_env/bin/python -m pip install -r requirements.txt
chmod +x scripts/auto_pipeline.py
sudo cp scripts/pcso-pipeline.service.example /etc/systemd/system/pcso-pipeline.service
sudo systemctl daemon-reload
sudo systemctl start pcso-pipeline.service
sudo systemctl status pcso-pipeline.service
```

Enable it at boot:

```bash
sudo systemctl enable pcso-pipeline.service
```

View logs:

```bash
journalctl -u pcso-pipeline.service -f
```

### Automation Test Plan

Test normal execution:

```bash important
cd /Users/jonasodones/Desktop/src/my_scraper
SYNCHRONIZE_CMD=true ./scripts/auto_pipeline.py
```

Test lock behavior by starting two runs in separate terminals:

```bash
SYNCHRONIZE_CMD=true ./scripts/auto_pipeline.py
SYNCHRONIZE_CMD=true ./scripts/auto_pipeline.py
```

The second run should wait for the first one to finish.

Test partial file writes in watch-only mode:

```bash
cd /Users/jonasodones/Desktop/src/my_scraper
SYNCHRONIZE_CMD=true WATCH_ONLY=1 WAIT_TIMEOUT=60 ./scripts/auto_pipeline.py
```

In another terminal:

```bash
cd /Users/jonasodones/Desktop/src/my_scraper
printf '[' > pcso_results.json
sleep 3
cp pcso_results.json.backup pcso_results.json
```

The pipeline should wait until the file size is stable before running analysis.

Test failed analysis handling:

```bash
SYNCHRONIZE_CMD=true PATH_TO_ANALYZER=/bad/path/analyze_pcso_results.py ./scripts/auto_pipeline.py
```

The pipeline should fail fast and log the error.

## Troubleshooting

### `ModuleNotFoundError`

Install dependencies:

```bash
./pcso_env/bin/python -m pip install -r requirements.txt
```

### Scraper returns a network or DNS error

Check your internet connection and try again. The scraper needs access to:

```text
https://www.pcso.gov.ph/searchlottoresult.aspx
```

### Scraper says no rows were parsed

The PCSO website structure may have changed. Check these parts of
`pcso_lottery_scraper.py`:

- ASP.NET form field names in the POST payload
- results table id: `cphContainer_cpContent_GridView1`

### `synchronize: command not found`

Set `SYNCHRONIZE_CMD=true` if no synchronization command is needed:

```bash
SYNCHRONIZE_CMD=true ./scripts/auto_pipeline.py
```

Or set it to the real command:

```bash
SYNCHRONIZE_CMD="/path/to/synchronize" ./scripts/auto_pipeline.py
```

### Pipeline times out waiting for `pcso_results.json`

Check:

- the scraper completed successfully
- `SCRAPER_CMD` points to the correct command
- `PROJECT_ROOT` is correct
- `pcso_results.json` is being written to the expected folder
- `logs/pipeline.log` for the exact failure

You can increase the timeout:

```bash
WAIT_TIMEOUT=1200 ./scripts/auto_pipeline.py
```

### Analysis cannot find a game

Check available game names in `pcso_results.json` or run the analyzer with one
of the exact names from the scraped data, such as:

- `Ultra Lotto 6/58`
- `Grand Lotto 6/55`
- `Superlotto 6/49`
- `Megalotto 6/45`
- `Lotto 6/42`
- `6D Lotto`
- `4D Lotto`
- `3D Lotto 2PM`
- `3D Lotto 5PM`
- `3D Lotto 9PM`
- `2D Lotto 2PM`
- `2D Lotto 5PM`
- `2D Lotto 9PM`

## Notes

- Use reasonable scraping frequency.
- Always verify important results against the official PCSO website.
- Historical frequency does not change the odds of a future independent draw.
- This project is for personal, educational, and analytical use.
