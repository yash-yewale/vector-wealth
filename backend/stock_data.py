"""
Shared stock data: aliases, peer groups, source quality weights, and sector queries.

Single source of truth — imported by agents.py, live_news_ingest.py, and opportunity_scanner.py.
"""
from __future__ import annotations


STOCK_ALIASES: dict[str, list[str]] = {
    # Banking & Finance
    "HDFCBANK": ["hdfc bank", "hdfc"],
    "ICICIBANK": ["icici bank", "icici"],
    "SBIN": ["state bank of india", "sbi"],
    "AXISBANK": ["axis bank", "axis"],
    "KOTAKBANK": ["kotak mahindra bank", "kotak bank", "kotak"],
    "INDUSINDBK": ["indusind bank", "indusind"],
    "BANDHANBNK": ["bandhan bank", "bandhan"],
    "FEDERALBNK": ["federal bank", "federal"],
    "IDFCFIRSTB": ["idfc first bank", "idfc first", "idfc"],
    "YESBANK": ["yes bank", "yes"],
    "BANKBARODA": ["bank of baroda", "bob", "baroda bank"],
    "CANBK": ["canara bank", "canara"],
    "PNB": ["punjab national bank", "pnb"],
    "UNIONBANK": ["union bank of india", "union bank"],
    "BAJFINANCE": ["bajaj finance", "baf", "bajaj fin"],
    "BAJAJFINSV": ["bajaj finserv", "bajaj financial services"],
    "CHOLAFIN": ["cholamandalam finance", "chola", "cholamandalam"],
    "MUTHOOTFIN": ["muthoot finance", "muthoot"],
    "MANAPPURAM": ["manappuram finance", "manappuram"],
    "SHRIRAMFIN": ["shriram finance", "shriram transport", "shriram"],
    "IIFL": ["iifl finance", "iifl"],
    "LICHSGFIN": ["lic housing finance", "lic housing"],
    "POONAWALLA": ["poonawalla fincorp", "poonawalla"],
    # IT & Tech
    "TCS": ["tata consultancy services", "tcs"],
    "INFY": ["infosys", "infy"],
    "WIPRO": ["wipro"],
    "HCLTECH": ["hcl technologies", "hcl tech", "hcl"],
    "TECHM": ["tech mahindra", "techmahindra"],
    "LTIM": ["ltimindtree", "lti mindtree", "mindtree"],
    "MPHASIS": ["mphasis"],
    "COFORGE": ["coforge", "niit technologies"],
    "PERSISTENT": ["persistent systems", "persistent"],
    "LTTS": ["l&t technology services", "lt technology"],
    "CYIENT": ["cyient"],
    # Oil & Gas
    "RELIANCE": ["reliance industries", "ril", "reliance", "mukesh ambani", "jio", "reliance jio"],
    "ONGC": ["oil and natural gas corporation", "ongc", "oil india"],
    "IOC": ["indian oil corporation", "indian oil", "ioc", "iocl"],
    "BPCL": ["bharat petroleum", "bpcl", "bharat petro"],
    "HINDPETRO": ["hindustan petroleum", "hpcl", "hp petrol"],
    "GAIL": ["gail india", "gail", "gas authority of india"],
    "PETRONET": ["petronet lng", "petronet"],
    "ATGL": ["adani total gas", "adani gas"],
    "IGL": ["indraprastha gas", "igl"],
    "MGL": ["mahanagar gas", "mgl"],
    # Auto & Auto Components
    "MARUTI": ["maruti suzuki", "maruti"],
    "TATAMOTORS": ["tata motors", "tata motor"],
    "M&M": ["mahindra and mahindra", "mahindra", "m&m"],
    "BAJAJ-AUTO": ["bajaj auto", "bajaj automobile"],
    "HEROMOTOCO": ["hero motocorp", "hero honda", "hero"],
    "EICHERMOT": ["eicher motors", "royal enfield", "eicher"],
    "ASHOKLEY": ["ashok leyland", "ashok"],
    "TVSMOT": ["tvs motor", "tvs motors", "tvs"],
    "ESCORTS": ["escorts kubota", "escorts"],
    "MRF": ["mrf", "mrf tyres", "mrf tyre", "madras rubber factory"],
    "APOLLOTYRE": ["apollo tyres", "apollo tyre"],
    "CEAT": ["ceat tyres", "ceat"],
    "BALKRISIND": ["balkrishna industries", "bkt tyres", "balkrishna"],
    "MOTHERSON": ["motherson sumi", "motherson", "samvardhana motherson"],
    "BHARATFORG": ["bharat forge", "bharatforge"],
    "SUNDRMFAST": ["sundram fasteners", "sundram"],
    "EXIDEIND": ["exide industries", "exide"],
    "AMARAJABAT": ["amara raja batteries", "amara raja", "amaron"],
    # FMCG
    "ITC": ["itc", "itc limited"],
    "HINDUNILVR": ["hindustan unilever", "hul", "unilever india"],
    "NESTLEIND": ["nestle india", "nestle", "maggi"],
    "BRITANNIA": ["britannia industries", "britannia"],
    "DABUR": ["dabur india", "dabur"],
    "MARICO": ["marico", "parachute"],
    "GODREJCP": ["godrej consumer products", "godrej consumer"],
    "COLPAL": ["colgate palmolive", "colgate"],
    "TATACONSUM": ["tata consumer products", "tata consumer", "tata tea"],
    "VBL": ["varun beverages", "varun", "pepsi bottler"],
    "UNITDSPR": ["united spirits", "diageo india"],
    "UBL": ["united breweries", "kingfisher"],
    "RADICO": ["radico khaitan", "radico"],
    "EMAMILTD": ["emami", "emami limited"],
    # Pharma & Healthcare
    "SUNPHARMA": ["sun pharma", "sun pharmaceutical"],
    "DRREDDY": ["dr reddys", "dr reddy's laboratories", "drreddy"],
    "CIPLA": ["cipla"],
    "DIVISLAB": ["divis laboratories", "divi's lab", "divis lab"],
    "LUPIN": ["lupin"],
    "AUROPHARMA": ["aurobindo pharma", "aurobindo"],
    "TORNTPHARM": ["torrent pharma", "torrent pharmaceuticals"],
    "ALKEM": ["alkem laboratories", "alkem"],
    "BIOCON": ["biocon"],
    "GLAND": ["gland pharma", "gland"],
    "ZYDUSLIFE": ["zydus lifesciences", "cadila healthcare", "zydus"],
    "IPCALAB": ["ipca laboratories", "ipca"],
    "NATCOPHAR": ["natco pharma", "natco"],
    "APOLLOHOSP": ["apollo hospitals", "apollo hospital"],
    "FORTIS": ["fortis healthcare", "fortis"],
    "MAXHEALTH": ["max healthcare", "max hospital"],
    "METROPOLIS": ["metropolis healthcare", "metropolis"],
    "LALPATHLAB": ["dr lal pathlabs", "lal path lab", "dr lal"],
    "THYROCARE": ["thyrocare", "thyrocare technologies"],
    # Cement & Building Materials
    "ULTRACEMCO": ["ultratech cement", "ultratech"],
    "AMBUJACEM": ["ambuja cements", "ambuja cement", "ambuja"],
    "ACC": ["acc cement", "acc limited", "acc"],
    "SHREECEM": ["shree cement", "shree cements"],
    "DALMIAZBHARAT": ["dalmia bharat", "dalmia cement"],
    "RAMCOCEM": ["ramco cements", "ramco cement"],
    "JKCEMENT": ["jk cement", "jk cements"],
    "BIRLACORPN": ["birla corporation", "birla cement"],
    "JSWSTEEL": ["jsw steel", "jindal south west steel"],
    "TATASTEEL": ["tata steel", "tata steel india"],
    "HINDALCO": ["hindalco", "hindalco industries", "novelis"],
    "VEDL": ["vedanta", "vedanta limited", "vedl"],
    "JINDALSTEL": ["jindal steel", "jindal steel and power", "jspl"],
    "SAIL": ["steel authority of india", "sail"],
    "NMDC": ["nmdc", "national mineral development corporation"],
    "COALINDIA": ["coal india", "coal india limited"],
    "APLAPOLLO": ["apl apollo", "apl apollo tubes"],
    # Infra & Engineering
    "LT": ["larsen and toubro", "l&t", "lt", "larsen & toubro"],
    "ADANIENT": ["adani enterprises", "adani", "gautam adani"],
    "ADANIPORTS": ["adani ports", "adani port"],
    "ADANIGREEN": ["adani green energy", "adani green"],
    "ADANIPOWER": ["adani power"],
    "NTPC": ["ntpc", "national thermal power"],
    "POWERGRID": ["power grid", "powergrid", "power grid corporation"],
    "TATAPOWER": ["tata power", "tata electricity"],
    "NHPC": ["nhpc", "national hydroelectric power"],
    "SJVN": ["sjvn", "satluj jal vidyut nigam"],
    "IRFC": ["indian railway finance corporation", "irfc"],
    "IRCTC": ["indian railway catering and tourism corporation", "irctc"],
    "RVNL": ["rail vikas nigam", "rvnl"],
    "IRCON": ["ircon international", "ircon"],
    "RITES": ["rites", "rites limited"],
    "BEL": ["bharat electronics", "bel", "bharat electronics limited"],
    "HAL": ["hindustan aeronautics", "hal", "hal india"],
    "BDL": ["bharat dynamics", "bdl"],
    "COCHINSHIP": ["cochin shipyard", "cochin ship", "csl"],
    "GRSE": ["garden reach shipbuilders", "grse"],
    "MAZDOCK": ["mazagon dock", "mazagon dock shipbuilders", "mdl"],
    "GESHIP": ["great eastern shipping", "ge shipping"],
    "SCI": ["shipping corporation of india", "sci"],
    "SIEMENS": ["siemens india", "siemens"],
    "ABB": ["abb india", "abb"],
    "CUMMINSIND": ["cummins india", "cummins"],
    "THERMAX": ["thermax"],
    # Telecom
    "BHARTIARTL": ["bharti airtel", "airtel", "bharti"],
    "VODAIDEA": ["vodafone idea", "vi", "vodafone", "idea cellular"],
    "INDUSTOWER": ["indus towers", "indus tower"],
    "TATACOMM": ["tata communications", "tata telecom"],
    # Retail & Consumer
    "DMART": ["avenue supermarts", "dmart", "d-mart"],
    "TRENT": ["trent", "westside", "zudio"],
    "ABFRL": ["aditya birla fashion", "abfrl", "pantaloons"],
    "SHOPERSTOP": ["shoppers stop"],
    "VMART": ["v-mart", "vmart"],
    "TITAN": ["titan company", "titan", "tanishq"],
    "PAGEIND": ["page industries", "jockey india"],
    "RELAXO": ["relaxo footwears", "relaxo"],
    "BATA": ["bata india", "bata"],
    "CAMPUS": ["campus activewear", "campus shoes"],
    "METRO": ["metro brands", "metro shoes"],
    # Insurance
    "SBILIFE": ["sbi life insurance", "sbi life"],
    "HDFCLIFE": ["hdfc life insurance", "hdfc life"],
    "ICICIPRULI": ["icici prudential life", "icici pru life"],
    "MAXFIN": ["max financial", "max life"],
    "LICI": ["life insurance corporation", "lic", "lic of india"],
    "GICRE": ["general insurance corporation", "gic re"],
    "NIACL": ["new india assurance", "new india"],
    "ICICIGI": ["icici lombard", "icici general"],
    "STARHEALTH": ["star health insurance", "star health"],
    "POLICYBZR": ["pb fintech", "policybazaar"],
    # Miscellaneous
    "ZOMATO": ["zomato"],
    "NYKAA": ["fsn e-commerce", "nykaa"],
    "PAYTM": ["one97 communications", "paytm", "one 97"],
    "CARTRADE": ["cartrade tech", "cartrade"],
    "DELHIVERY": ["delhivery", "delhivery logistics"],
    "INDIGO": ["interglobe aviation", "indigo airlines", "indigo"],
    "SPICEJET": ["spicejet", "spice jet"],
    "PGHH": ["procter and gamble hygiene", "p&g india"],
    "3MINDIA": ["3m india", "3m"],
    "WHIRLPOOL": ["whirlpool india", "whirlpool"],
    "VOLTAS": ["voltas", "tata voltas"],
    "BLUESTAR": ["blue star", "bluestar"],
    "HAVELLS": ["havells india", "havells"],
    "CROMPTON": ["crompton greaves consumer", "crompton"],
    "ORIENTEL": ["orient electric", "orient"],
    "VGUARD": ["v-guard", "vguard"],
    "POLYCAB": ["polycab india", "polycab"],
    "KAYNES": ["kaynes technology", "kaynes"],
    "DIXON": ["dixon technologies", "dixon"],
    "AMBER": ["amber enterprises", "amber"],
    "ASIANPAINT": ["asian paints", "asian paint"],
    "BERGEPAINT": ["berger paints", "berger paint"],
    "KANSAINER": ["kansai nerolac", "nerolac"],
    "PIDILITIND": ["pidilite industries", "pidilite", "fevicol", "m-seal"],
    "ASTRAL": ["astral", "astral pipes"],
    "SUPREMEIND": ["supreme industries", "supreme pipes"],
    "PRINCEPIPE": ["prince pipes", "prince pipe"],
    "FINOLEX": ["finolex industries", "finolex cables", "finolex"],
    "JUBLFOOD": ["jubilant foodworks", "dominos india", "jubilant"],
    "WESTLIFE": ["westlife foodworld", "mcdonalds india", "westlife"],
    "DEVYANI": ["devyani international", "devyani", "yum brands india"],
    "SAPPHIRE": ["sapphire foods", "kfc india", "pizza hut india"],
}


SOURCE_QUALITY_WEIGHTS: dict[str, float] = {
    "economictimes.com": 1.12,
    "the times of india": 1.0,
    "businessline": 1.08,
    "moneycontrol": 1.08,
    "livemint": 1.08,
    "mint": 1.08,
    "reuters": 1.15,
    "bloomberg": 1.15,
    "cnbc": 1.07,
    "historical_csv": 0.9,
}


PEER_GROUPS: dict[str, list[str]] = {
    # Banking
    "HDFCBANK": ["ICICIBANK", "KOTAKBANK", "SBIN", "AXISBANK"],
    "ICICIBANK": ["HDFCBANK", "KOTAKBANK", "SBIN", "AXISBANK"],
    "KOTAKBANK": ["HDFCBANK", "ICICIBANK", "SBIN", "AXISBANK"],
    "SBIN": ["HDFCBANK", "ICICIBANK", "KOTAKBANK", "PNB"],
    "AXISBANK": ["HDFCBANK", "ICICIBANK", "KOTAKBANK", "SBIN"],
    "PNB": ["SBIN", "BANKBARODA", "BANKINDIA", "CANBK"],
    # IT
    "TCS": ["INFY", "WIPRO", "HCLTECH", "TECHM"],
    "INFY": ["TCS", "WIPRO", "HCLTECH", "TECHM"],
    "WIPRO": ["TCS", "INFY", "HCLTECH", "TECHM"],
    "HCLTECH": ["TCS", "INFY", "WIPRO", "TECHM"],
    "TECHM": ["TCS", "INFY", "WIPRO", "HCLTECH"],
    # Auto
    "MARUTI": ["TATAMOTORS", "M&M", "BAJAJ-AUTO", "HEROMOTOCO"],
    "TATAMOTORS": ["MARUTI", "M&M", "BAJAJ-AUTO", "EICHERMOT"],
    "M&M": ["MARUTI", "TATAMOTORS", "BAJAJ-AUTO", "ASHOKLEY"],
    "BAJAJ-AUTO": ["MARUTI", "TATAMOTORS", "HEROMOTOCO", "TVSMOTORS"],
    "HEROMOTOCO": ["BAJAJ-AUTO", "TVSMOTORS", "EICHERMOT", "MARUTI"],
    # Tyres
    "MRF": ["APOLLOTYRE", "CEAT", "BALKRISIND", "JKTYRE"],
    "APOLLOTYRE": ["MRF", "CEAT", "BALKRISIND", "JKTYRE"],
    "CEAT": ["MRF", "APOLLOTYRE", "BALKRISIND", "JKTYRE"],
    # Pharma
    "SUNPHARMA": ["DRREDDY", "CIPLA", "DIVISLAB", "LUPIN"],
    "DRREDDY": ["SUNPHARMA", "CIPLA", "DIVISLAB", "LUPIN"],
    "CIPLA": ["SUNPHARMA", "DRREDDY", "DIVISLAB", "LUPIN"],
    # Defense
    "HAL": ["BEL", "BHARATFORGE", "MAZAGON", "COCHINSHIP"],
    "BEL": ["HAL", "BHARATFORGE", "MAZAGON", "COCHINSHIP"],
    "COCHINSHIP": ["HAL", "BEL", "MAZAGON", "GRSE"],
    "MAZAGON": ["HAL", "BEL", "COCHINSHIP", "GRSE"],
    # Metals
    "TATASTEEL": ["JSWSTEEL", "HINDALCO", "VEDL", "SAIL"],
    "JSWSTEEL": ["TATASTEEL", "HINDALCO", "VEDL", "SAIL"],
    "HINDALCO": ["TATASTEEL", "JSWSTEEL", "VEDL", "NMDC"],
    # Oil & Gas
    "RELIANCE": ["ONGC", "IOC", "BPCL", "GAIL"],
    "ONGC": ["RELIANCE", "IOC", "BPCL", "GAIL"],
    "IOC": ["RELIANCE", "ONGC", "BPCL", "HINDPETRO"],
    # FMCG
    "HINDUNILVR": ["ITC", "NESTLEIND", "BRITANNIA", "DABUR"],
    "ITC": ["HINDUNILVR", "NESTLEIND", "BRITANNIA", "DABUR"],
    "NESTLEIND": ["HINDUNILVR", "ITC", "BRITANNIA", "DABUR"],
    # Power
    "NTPC": ["POWERGRID", "TATAPOWER", "ADANIPOWER", "JSWENERGY"],
    "POWERGRID": ["NTPC", "TATAPOWER", "ADANIGREEN", "TORNTPOWER"],
    "TATAPOWER": ["NTPC", "POWERGRID", "ADANIPOWER", "JSWENERGY"],
    # Telecom
    "BHARTIARTL": ["RELIANCE", "IDEA", "TATACOMM"],
    "IDEA": ["BHARTIARTL", "TATACOMM"],
    # Cement
    "ULTRACEMCO": ["SHREECEM", "ACC", "AMBUJACEM", "DALMIACEM"],
    "ACC": ["ULTRACEMCO", "SHREECEM", "AMBUJACEM", "DALMIACEM"],
    "AMBUJACEM": ["ULTRACEMCO", "SHREECEM", "ACC", "DALMIACEM"],
}


SECTOR_QUERIES: list[str] = [
    # Banks & Finance
    "HDFC Bank OR ICICI Bank OR SBI OR Axis Bank OR Kotak Bank OR Bajaj Finance",
    "Yes Bank OR IndusInd Bank OR Federal Bank OR RBL Bank OR IDFC First Bank",
    # IT & Tech
    "TCS OR Infosys OR Wipro OR HCL Tech OR Tech Mahindra OR LTIMindtree",
    # Auto
    "Maruti Suzuki OR Tata Motors OR Mahindra OR Bajaj Auto OR Hero MotoCorp OR Eicher Motors",
    # Pharma
    "Sun Pharma OR Dr Reddy OR Cipla OR Divis Labs OR Lupin OR Aurobindo Pharma",
    # Oil & Gas
    "Reliance Industries OR ONGC OR Indian Oil OR BPCL OR HPCL OR GAIL",
    # FMCG
    "ITC OR Hindustan Unilever OR Nestle India OR Britannia OR Dabur OR Marico",
    # Metals & Mining
    "Tata Steel OR JSW Steel OR Hindalco OR Vedanta OR Coal India OR NMDC",
    # Cement
    "UltraTech Cement OR Shree Cement OR ACC OR Ambuja Cements OR Dalmia Bharat",
    # Power & Utilities
    "NTPC OR Power Grid OR Tata Power OR Adani Power OR Adani Green Energy",
    # Infra & Capital Goods
    "Larsen Toubro OR Adani Enterprises OR Adani Ports OR GMR Infra",
    "DLF OR Godrej Properties OR Oberoi Realty OR Prestige Estates",
    # Telecom & Media
    "Bharti Airtel OR Vodafone Idea OR Indus Towers OR Tata Communications",
    # New Age & E-commerce
    "Zomato OR Nykaa OR Paytm OR Delhivery OR PolicyBazaar",
    # Defence & Shipbuilding
    "HAL OR BEL OR Bharat Forge OR Mazagon Dock OR Cochin Shipyard",
    # Insurance
    "SBI Life OR HDFC Life OR ICICI Prudential Life OR LIC OR Star Health",
]


TICKER_SUFFIX_SPLITS = (
    "BANK", "STEEL", "MOTORS", "POWER", "ENERGY",
    "PHARMA", "FINANCE", "FIN", "INFRA", "TECH", "INDIA", "LIFE",
)

GENERIC_STOCK_TERMS = {
    "bank", "india", "indian", "ltd", "limited", "inc",
    "company", "co", "corp", "group", "industries", "services",
}

QUERY_STOPWORDS = {
    "what", "is", "the", "on", "for", "and", "with",
    "from", "this", "that", "about", "sentiment", "stock", "ticker", "market",
}
