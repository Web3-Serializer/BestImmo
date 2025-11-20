from modules import LeFigaro, SeLoger, BienIci, LogicImmo, IADFrance, NotairesFrance, VinciImmobilier, ImmobilierFrance
from modules.utils import logger
import threading, time

class Main:

    def __init__(self):
        self.runningThreads = []
        self.modules = [
            LeFigaro.LeFigaroModule(),
            SeLoger.SeLogerModule(),
            LogicImmo.LogicImmoModule(),
            BienIci.BienIciModule(),
            IADFrance.IADFranceModule(),
            NotairesFrance.NotairesFranceModule(),
            VinciImmobilier.VinciImmobilierModule(),
            ImmobilierFrance.ImmobilierFranceModule()
        ]
        self.logger = logger.Logger("Main")
        self.logger.info(f'Loaded {len(self.modules)} module(s)')


    def Run(self):
        successfullyRan = 0
        
        self.logger.info('Running modules...')
        # runs the modules each one by one
        for m in self.modules:
            try:
                t = threading.Thread(target=m.start)
                self.runningThreads.append(t)
                t.start()
                successfullyRan += 1
                self.logger.success(f'Module "{m.name}" has been started, and is now crawling.')
            except Exception as err:
                self.logger.error(f'Failed to launch module named "{m.name}"! (Error: {err})')

        self.logger.info(f'{successfullyRan} module(s) are runnings.')


        while True:
            totalFound = 0
            for m in self.modules:
                self.logger.warning(f' Module > {m.name} | ADs Scrapped: {m.current_scrapped_ads}/{m.total_ads_found}')
                totalFound += int(m.current_scrapped_ads)
            self.logger.warning(f' Main > Total ADs Scrapped: {totalFound} | Waiting 5s before refreshing...')
            time.sleep(5)


if __name__ == "__main__":
    m = Main()
    m.Run()

