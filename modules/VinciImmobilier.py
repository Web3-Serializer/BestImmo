from . import CrawlerModule
from .utils.logger import Logger
from datetime import datetime
import time

class VinciImmobilierModule(CrawlerModule):

    def __init__(self):
        super().__init__("VinciImmobilier", "Module for vinci-immobilier.com", True, False)
        self.logger = Logger(self.name)
        self.base_url = "https://www.vinci-immobilier.com"
        self.logger.success('Module loaded.')

        self.set_random_proxy()

        self.tls_session.client_identifier = "chrome_137"
        self.tls_session.random_tls_extension_order = True
        self.tls_session.headers.update({
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
            "ocp-apim-subscription-key": "681b3f5d274440a4af802254187930bc",
            "referer": "https://www.vinci-immobilier.com/recherche"
        })

    def getAds(self, page: int = 1, pageSize: int = 10):
        try:
            url = f"https://www.vinci-immobilier.com/api/offres/recherche/lot?medias[]=Site%20R%C3%A9sidentiel%20%2B%20Extranet%20client&phase_commerciale[]=Avant-premi%C3%A8re&phase_commerciale[]=Commercialisation&phase_commerciale[]=Lancement&site=v4&items_per_page={pageSize}&page={page}"
            resp = self.tls_session.get(url)

            if resp.status_code == 200:
                return resp.json()
            else:
                print(resp.content)
                self.logger.error(f"HTTP Error: {resp.status_code}")
                return False
        except Exception as e:
            self.logger.error(f"Error fetching ads: {str(e)}")
            return False

    def normalize_and_save_ads(self, ads_data):
        ads = ads_data.get('results', [])
        if not ads:
            self.logger.warning("No ads data found in response")
            return 0

        saved_count = 0

        for ad in ads:
            try:
                typologie = ad.get("field_typologie_lot", "")
                surface = float(ad.get("field_surface_habitable", 0))
                piece_count = typologie.replace("T", "") if typologie and "T" in typologie else None

                normalized = self.normalize_ad(
                    id=str(ad.get("field_id_crm")),
                    source="vinci_immobilier",
                    url=f"https://www.vinci-immobilier.com/programmes/{ad.get('id_programme')}",
                    title=f"{ad.get('field_nature')} {typologie or ''} - {surface or '?'} m²",
                    description=ad.get("field_programme", ""),
                    property_type=ad.get("field_nature", "").lower(),
                    transaction_type="vente",
                    price=float(ad.get("field_prix_tva_reduite") or 0),
                    city=ad.get("ville"),
                    postal_code=ad.get("code_postal"),
                    surface=surface,
                    rooms=int(piece_count) if piece_count and piece_count.isdigit() else None,
                    bedrooms=None,
                    photos=[],
                    agency_name="Vinci Immobilier",
                    agency_phone="+33 01 55 38 80 00",
                    created_at=ad.get("field_date_modification"),
                    updated_at=ad.get("field_date_modification"),
                )

                self._shared_db.get_collection("ads").update_one(
                    {"id": normalized["id"]},
                    {"$set": normalized},
                    upsert=True
                )
                saved_count += 1
            except Exception as e:
                self.logger.error(f"Error normalizing ad {ad.get('field_id_crm', 'unknown')}: {str(e)}")

        return saved_count

    def start(self):
        if not self.enabled:
            raise Exception("This module is currently disabled.")

        page = 1
        page_size = 10
        total_saved = 0

        while True:
            self.logger.info(f"Fetching Vinci Immobilier ads... (Page {page})")
            response = self.getAds(page=page, pageSize=page_size)

            if response is False:
                self.logger.warning('Error while fetching data, switching proxy, waiting 5s before retrying...')
                self.set_random_proxy()
                time.sleep(5)
                continue

            total_items = int(response.get("pager", {}).get("total_items", 0))
            if total_items > self.total_ads_found:
                self.total_ads_found = total_items

            items = response.get("results", [])

            # if not items:
            #     self.logger.info("No more ads found, stopping...")
            #     break

            saved_count = self.normalize_and_save_ads(response)
            total_saved += saved_count
            self.current_scrapped_ads += saved_count

            self.logger.success(f"Page {page}: Processed and saved {saved_count} ads to database")

            if len(items) < page_size:
                self.logger.info("Reached end of listings")
                break

            if total_saved >= total_items and total_saved > 0  :
                self.logger.info("All available ads have been processed")
                break

            page += 1

        self.logger.success(f"Finished! Total ads saved: {total_saved}")
        return total_saved
