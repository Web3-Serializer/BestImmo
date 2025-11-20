# 🏡 French-eState-Scrapper

Modular scraper for French real estate listings from major platforms like Le Figaro, SeLoger, LogicImmo, BienIci, IAD, Notaires, Vinci, and Immobilier France. Designed for data analysis.<br>

*Note: This was built in 1 day and the code quality is poor.*

## ❓ About

This scraper is designed for **educational purposes only**. It collects real estate listings from multiple French property platforms without overloading their servers. **Do not abuse the APIs**.

## ✅ Supported Platforms

* `LeFigaro`
* `SeLoger`
* `LogicImmo`
* `BienIci`
* `IADFrance`
* `NotairesFrance`
* `VinciImmobilier`
* `ImmobilierFrance`

## 💫 Features

* Collects property data: type, location, price, surface, number of rooms, and seller info.
* Modular architecture for easy extension to new platforms.
* Stores listings in **MongoDB** for easy querying and analysis.

## 🛠 Installation

```bash
git clone https://github.com/Web3-Serializer/French-eState-Scrapper.git
cd French-eState-Scrapper
```

Make sure MongoDB is running locally or provide a connection URI in the configuration.

## 📜 Usage

```python
from scrapers import LeFigaro, SeLoger, LogicImmo

# Example: scrape listings from Le Figaro
scraper = LeFigaro.LeFigaroModule()
scraper.start()  # start and stores results in MongoDB
```

> ⚠️ **Warning:** This project is for educational purposes only. Respect the websites' terms of service.
