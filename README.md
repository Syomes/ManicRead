# ManicRead

## Overview

The Linux version of [ManicTime](https://www.manictime.com/download/linux) does not render a UI locally — it only provides timeline tracking for each application, ultimately generating a `sqlite` database file (typically located in `~/.config/manictime/`), along with a `Screenshots` directory for storage.

As of 2025.06.24, only `ManicTimeReports.db` is used and read as the data source; the backend searches the `Screenshots` directory to display images. The interface is rendered as a web page, primarily using [NiceGUI](https://nicegui.io), with charts rendered via embedded [HighCharts](https://www.highcharts.com).

## Features

- **Daily** — Track by specific date
  ![](./img/daily.png)

- **Period** — Track by time range
  ![](./img/period.png)

## Usage

> [!NOTE]
> ManicTime data files are typically stored in `~/.config/manictime/`. If the path has been modified, check your actual location.

Python 3.10+ is recommended.

### Clone

```bash
git clone https://github.com/SevenSec114/ManicRead.git
```

### Dependencies

```bash
pip install -r requirements.txt
```

### Run

```bash
python main.py
```

This will start a web server at `http://127.0.0.1:8080` by default.

## License

This project is licensed under the Apache License 2.0 — see the [LICENSE](LICENSE) file for details.

## [Changelog](changelog.md)
