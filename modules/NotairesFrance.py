from . import CrawlerModule
import urllib.parse
from .utils.logger import Logger
import time
from datetime import datetime

class NotairesFranceModule(CrawlerModule):

    def __init__(self):
        super().__init__("NotairesFrance", "Module for immobilier.notaires.fr", True, False)
        self.logger = Logger(self.name)
        self.base_url = "https://www.immobilier.notaires.fr"
        self.logger.success('Module loaded.')

        self.set_random_proxy()

        self.tls_session.client_identifier = "chrome_137"
        self.tls_session.random_tls_extension_order = True
        self.tls_session.headers.update({
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
            "accept": "application/json, text/plain, */*",
            "accept-language": "fr-FR,fr;q=0.9,en;q=0.8",
            "referer": "https://www.immobilier.notaires.fr/",
        })

    def getAds(self, page: int = 1, pageSize: int = 100):
        try:
            params = {
                'offset': (page - 1) * pageSize,
                'page': page,
                'parPage': pageSize,
                'perimetre': '',
                'typeTransactions': 'VENTE,VNI,VAE'
            }

            url = f'{self.base_url}/pub-services/inotr-www-annonces/v1/annonces'
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
        ads = ads_data.get('annonceResumeDto', [])
        if not ads:
            self.logger.warning("No ads data found in response")
            return 0

        saved_count = 0

        for ad in ads:
            try:
                property_type_mapping = {
                    'TER': 'terrain',
                    'APP': 'appartement',
                    'MAI': 'maison',
                    'LOC': 'local commercial'
                }
                
                property_type = property_type_mapping.get(ad.get('typeBien'), ad.get('typeBien'))
                
                normalized = self.normalize_ad(
                    id=str(ad.get('annonceId')),
                    source="notaires_france",
                    url=ad.get('urlDetailAnnonceFr'),
                    title=f"{property_type.capitalize()} {ad.get('nbPieces') or '?'} pièce(s) {ad.get('surface') or '?'} m²",
                    description=ad.get('descriptionFr', ''),
                    property_type=property_type,
                    transaction_type=ad.get('typeTransaction', 'vente').lower(),
                    price=ad.get('prixAffiche'),
                    city=ad.get('communeNom'),
                    postal_code=ad.get('codePostal'),
                    surface=ad.get('surface'),
                    rooms=ad.get('nbPieces'),
                    bedrooms=ad.get('nbChambres'),
                    photos=[ad.get('urlPhotoPrincipale')] if ad.get('urlPhotoPrincipale') else [],
                    agency_name=None,
                    agency_phone=ad.get('telephone'),
                    created_at=ad.get('dateCreation'),
                    updated_at=ad.get('dateMaj'),
                )

                self._shared_db.get_collection("ads").update_one(
                    {"id": normalized["id"]},
                    {"$set": normalized},
                    upsert=True
                )
                saved_count += 1
            except Exception as e:
                self.logger.error(f"Error normalizing ad {ad.get('annonceId', 'unknown')}: {str(e)}")

        return saved_count

    def start(self):
        if not self.enabled:
            raise Exception("This module is currently disabled.")

        page = 1
        page_size = 100
        total_saved = 0

        while True:
            self.logger.info(f"Fetching listings from Notaires France... (Page {page})")
            response = self.getAds(page=page, pageSize=page_size)

            if response is False:
                self.logger.warning('Error while fetching data, switching proxy, waiting 5s before retrying...')
                self.set_random_proxy()
                time.sleep(5)
                continue

            total_items = response.get('nbTotalAnnonces', 0)
            if total_items > self.total_ads_found:
                self.total_ads_found = total_items

            self.logger.info(f"Total ads available: {total_items}")
            items = response.get('annonceResumeDto', [])

            
            # if not items:
            #     self.logger.info("No more ads found, stopping...")
            #     break

            ads_count = len(items)
            self.logger.info(f"Found {ads_count} ads on page {page}")

            saved_count = self.normalize_and_save_ads(response)
            total_saved += saved_count

            self.logger.success(f"Page {page}: Processed and saved {saved_count} ads to database")
            self.current_scrapped_ads += saved_count


            if ads_count < page_size:
                self.logger.info("Reached end of listings")
                break

            if total_saved >= total_items and total_saved > 0  :
                self.logger.info("All available ads have been processed")
                break

            page += 1
            time.sleep(1)

        self.logger.success(f"Finished! Total ads saved: {total_saved}")
        return total_saved
