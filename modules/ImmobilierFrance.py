from . import CrawlerModule
import urllib.parse
from .utils.logger import Logger
import time

class ImmobilierFranceModule(CrawlerModule):

    def __init__(self):
        super().__init__("ImmobilierFrance", "Module for immobilier-france.fr", True, False)
        self.logger = Logger(self.name)
        self.base_url = "https://api.immobilier-france.fr"
        self.logger.success('Module loaded.')

        self.set_random_proxy()

        self.tls_session.client_identifier = "chrome_137"
        self.tls_session.random_tls_extension_order = True
        self.tls_session.headers.update({
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
            "accept": "application/json, text/plain, */*",
            "referer": "https://www.immobilier-france.fr/",
        })

    def get_total_ads(self):
        try:
            url = f"{self.base_url}/api/ads/pagination"
            params = {
                "priceUnit": "total",
                "typeOfSale": "BUY",
                "limit": 1,
                "page": 1
            }
            resp = self.tls_session.get(url, params=params)
            if resp.status_code == 200:
                return resp.json().get("total", 0)
            else:
                self.logger.error(f"Failed to fetch total ads count. HTTP {resp.status_code}")
                return 0
        except Exception as e:
            self.logger.error(f"Error getting total ads count: {str(e)}")
            return 0

    def getAds(self, page: int = 1, pageSize: int = 20):
        try:
            url = f"{self.base_url}/api/ads/without-pagination"
            params = {
                "priceUnit": "total",
                "typeOfSale": "BUY",
                "limit": pageSize,
                "page": page
            }
            resp = self.tls_session.get(url, params=params)
            if resp.status_code == 200:
                return resp.json()
            else:
                self.logger.error(f"HTTP Error: {resp.status_code}")
                return False
        except Exception as e:
            self.logger.error(f"Error fetching ads: {str(e)}")
            return False

    def normalize_and_save_ads(self, ads_data):
        if not ads_data:
            self.logger.warning("No ads data found in response")
            return 0

        saved_count = 0

        for ad in ads_data:
            try:
                property_type_mapping = {
                    "APARTMENT": "appartement",
                    "HOUSE": "maison"
                }
                property_type = property_type_mapping.get(ad.get("typeOfProperty"), ad.get("typeOfProperty"))

                normalized = self.normalize_ad(
                    id=ad.get("_id"),
                    source="immobilier_france",
                    url=f"https://www.immobilier-france.fr/search/{ad.get('_id')}",
                    title=ad.get("title"),
                    description=ad.get("generatedDescription"),
                    property_type=property_type,
                    transaction_type="vente",
                    price=ad.get("price"),
                    city=ad.get("city"),
                    postal_code=ad.get("postal"),
                    surface=ad.get("surfaceArea"),
                    rooms=ad.get("countRooms"),
                    bedrooms=ad.get("countBedrooms"),
                    photos=ad.get("pictures", []),
                    agency_name=None,
                    agency_phone=None,
                    created_at=ad.get("lastCrawlAt"),
                    updated_at=ad.get("lastCrawlAt")
                )

                self._shared_db.get_collection("ads").update_one(
                    {"id": normalized["id"]},
                    {"$set": normalized},
                    upsert=True
                )
                saved_count += 1
            except Exception as e:
                self.logger.error(f"Error normalizing ad {ad.get('_id', 'unknown')}: {str(e)}")

        return saved_count

    def start(self):
        if not self.enabled:
            raise Exception("This module is currently disabled.")

        page = 1
        page_size = 20
        total_saved = 0
        total_ads = self.get_total_ads()
        if total_ads > self.total_ads_found:
            self.total_ads_found = total_ads

        while True:
            self.logger.info(f"Fetching listings from Immobilier France... (Page {page})")
            response = self.getAds(page=page, pageSize=page_size)

            if response is False:
                self.logger.warning('Error while fetching data, switching proxy, waiting 5s before retrying...')
                self.set_random_proxy()
                time.sleep(5)
                continue

            # if not response:
            #     self.logger.info("No more ads found, stopping...")
            #     break

            ads_count = len(response)
            self.logger.info(f"Found {ads_count} ads on page {page}")

            saved_count = self.normalize_and_save_ads(response)
            total_saved += saved_count

            self.logger.success(f"Page {page}: Processed and saved {saved_count} ads to database")
            self.current_scrapped_ads += saved_count

            if ads_count < page_size:
                self.logger.info("Reached end of listings")
                break

            if total_saved >= total_ads and total_saved > 0  :
                self.logger.info("All available ads have been processed")
                break

            page += 1
            time.sleep(1)

        self.logger.success(f"Finished! Total ads saved: {total_saved}")
        return total_saved
