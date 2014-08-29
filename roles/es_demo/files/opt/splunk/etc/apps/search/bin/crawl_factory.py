import crawl


import crawl_files
import crawl_network

def getCrawler(name, mgr, args):
    crawler = None
    if name.lower().startswith("file"):
        crawler = crawl_files.FileCrawler(mgr, args)
    elif name.lower().startswith("net"):
        crawler = crawl_network.NetworkCrawler(mgr, args)
    return crawler

def getCrawlerNames():
    return ["files", "net"]


