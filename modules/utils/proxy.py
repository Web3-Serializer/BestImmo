

def load_proxies():
    with open('./inputs/proxies.txt', 'r') as prxfile:
        proxies = prxfile.read().splitlines()
    prxfile.close()
    return proxies
    