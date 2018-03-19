from io import BytesIO
from json import dumps
from unittest import TestCase, mock
from unittest.mock import Mock
from zipfile import ZipInfo

import data_gathering_subsystem.data_modules.locations.locations as locations

DATA = "1138958	Kabul	Kabul	Cabool,Caboul,Cabul,Cabul - kabl,Cabul - کابل,Cabura,Cabúl,Caubul,Gorad Kabul,KBL,Kabil,Kaboel,Kabol,Kaboul,Kabul,Kabula,Kabulas,Kabuli,Kabulo,Kabura,Kabúl,Kabûl,Kampoul,Kobul,Kubha,Kábul,Kâbil,Kābol,ka bu er,kabl,kabul,kabula,kabuli,kaburu,kabwl,kapul,ke bu er,khabul,Καμπούλ,Горад Кабул,Кабул,Кобул,Քաբուլ,קאבול,كابل,كابۇل,کابل,کابول,काबुल,কাবুল,ਕਾਬੁਲ,କାବୁଲ,காபூல்,ಕಾಬುಲ್,കാബൂൾ,කාබුල්,คาบูล,ཁ་པལ།,ཁ་པུལ།,ქაბული,ካቡል,ទីក្រុងកាបូល,カブール,カーブル,喀布尔,喀布爾,카불	34.52813	69.17233	P	PPLC	AF		13				3043532		1798	Asia/Kabul	2014-02-28\n" + "360630	Cairo	Cairo	Al Qahirah,Al Qāhirah,CAI,Caire,Cairo,Cairo - alqahrt,Cairo - القاهرة,Cairu,Cairus,Caïro,El Caire,El Cairo,El Kahira,El Kahirah,El-Qahira,El-Qâhira,Il Cairo,Kaherah,Kahira,Kahirae,Kahire,Kahirä,Kair,Kaira,Kairas,Kairo,Kairó,Kajro,Kayro,Kaíró,Kaïro,Káhira,Le Caire,Lo Cayiro,Lungsod ng Cairo,Masr,Misr,Qahirə,alqahrt,kai luo,kailo,kairo,keyro,khiro,qahrh,qhyr,Ël Cairo,Ël Càiro,Κάιρο,Каир,Каиро,Кайро,Каїр,קהיר,القاهرة,قاهره,قاھىرە,قاہرہ,கெய்ரோ,ไคโร,ཁ་ཡི་རོ,ქაირო,ካይሮ,カイロ,开罗,카이로	30.06263	31.24967	P	PPLC	EG		11				7734614		23	Africa/Cairo	2015-06-03\n" + "3598132	Guatemala City	Guatemala City	Cidade da Guatemala,Citta del Guatemala,Città del Guatemala,Ciudad Guatemala,Ciudad de Guatemala,Ciutat de Guatemala,GUA,Guate,Guatemala,Guatemala City,Guatemala Hiria,Guatemala by,Guatemala la Nueva,Guatemala-Stadt,Guatemala-Urbo,Guatemala-stad,Gvatemala,Gvatemalurbo,Gwatemala,New Guatemala,Nueva Guatemala,Nueva Guatemala de la Asuncion,Nueva Guatemala de la Asunción,Pole tes Gouatemalas,Santiago de Guatimala,gua de ma la shi,guatemarashiti,gwatemalla si,gwatemallasiti,kawtemalasiti,mdynt ghwatymala,shhr gwatmala,Πόλη της Γουατεμάλας,Гватемала,גואטמלה סיטי,גוואטמלה סיטי,شهر گواتمالا,مدينة غواتيمالا,กัวเตมาลาซิตี,グアテマラシティ,瓜地馬拉市,과테말라 시,과테말라시티	14.64072	-90.51327	P	PPLC	GT		07				994938		1508	America/Guatemala	2017-06-20\n" + "1273294	Delhi	Delhi	DEL,Daehli,Dehli,Dehlī,Delchi,Delhi,Delhio,Delhí,Delhî,Deli,Delis,Delkhi,Dellium,Delí,Dilhi,Dilli,Dillí,Dillī,Dähli,Déhli,Faritani Delhi,Gorad Dehli,New Delhi,Old Delhi,Sahdzahanabad,Stare Deli,de li,dehali,deli,delli,deri,dhilli,dhly,dhly qdym,dil'hi,dili,dilli,dlhy,dly,dlھy,dylhy,na'i dilli,prany dہly,tilli,Šáhdžahanabád,Δελχί,Горад Дэлі,Дели,Делхи,Делі,Деҳли,Старе Делі,Դելի,דלהי,דעלהי,دلهي,دلھی,دلی,دهلي,دهلی قدیم,ديلهى,دہلی,دێھلی,پرانی دہلی,ډېلي,ދިއްލީ,दिल्ली,देहली,नई दिल्ली,দিল্লি,দিল্লী,ਦਿੱਲੀ,દિલ્હી,ଦିଲ୍ଲୀ,தில்லி,ఢిల్లీ,ದೆಹಲಿ,ഡെൽഹി,เดลี,დელი,デリー,德里,델리	28.65195	77.23149	P	PPLA	IN		07				10927986		227	Asia/Kolkata	2017-10-30\n" + "3530597	Mexico City	Mexico City	Cidade de Mexico,Cidade de México,Cidade do Mexico,Cidade do México,Cita du Messicu,Citta del Messico,Città del Messico,Cità dû Messicu,Cità dû Mèssicu,Ciudad Mexico,Ciudad de Mejico,Ciudad de Mexico,Ciudad de Méjico,Ciudad de México,Ciutat de Mexic,Ciutat de Mèxic,Lungsod ng Mexico,Lungsod ng México,MEX,Mehiko,Mekhiko,Meksikas,Meksiko,Meksiko Siti,Meksikurbo,Meksyk,Mexico,Mexico City,Mexico D.F.,Mexico DF,Mexico Distrito Federal,Mexico by,Mexico-stad,Mexicopolis,Mexiko,Mexiko Hiria,Mexiko-Stadt,Mexikoborg,Mexíkóborg,México,México Distrito Federal,Nkoyo,Pole tou Mexikou,Valle de Mexico,Valle de México,mdynt mksykw,megsiko si,megsikositi,mekishikoshiti,meksiko siti,meksikositi,mkzykw,mkzykwsyty,mo xi ge cheng,mqsyqw syty,Πόλη του Μεξικού,Мексико,Мексико Сити,Мехико,Мехіко,מקסיקו סיטי,مدينة مكسيكو,مکزیکو,مکزیکوسیتی,مېكسىكا شەھىرى,मेक्सिको सिटी,เม็กซิโกซิตี,მეხიკო,メキシコシティ,墨西哥城,멕시코 시,멕시코시티	19.42847	-99.12766	P	PPLC	MX		09	015			12294193		2240	America/Mexico_City	2017-06-22\n"
DATA = DATA.encode()

LOCATIONS = {'Cairo': {'_id': 1, 'country_code': 'EG', 'latitude': 30.06263, 'longitude': 31.24967},
             'Delhi': {'_id': 2, 'country_code': 'IN', 'latitude': 28.65195, 'longitude': 77.23149},
             'Guatemala City': {'_id': 3, 'country_code': 'GT', 'latitude': 14.64072, 'longitude': -90.51327},
             'Mexico City': {'_id': 4, 'country_code': 'MX', 'latitude': 19.42847, 'longitude': -99.12766},
             'Kabul': {'_id': 9, 'country_code': 'AF', 'latitude': 34.52813, 'longitude': 69.17233}}


class TestLocations(TestCase):

    @classmethod
    def setUpClass(cls):
        locations.instance(log_to_stdout=False, log_to_telegram=False).remove_files()

    def tearDown(self):
        if hasattr(self, 'data_collector'):
            self.data_collector.remove_files()

    def test_instance(self):
        self.assertIs(locations.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False),
                      locations.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False))
        i1 = locations.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False)
        i1._transition_state = i1._FINISHED
        self.assertIsNot(i1, locations.instance(log_to_file=False, log_to_stdout=False, log_to_telegram=False))

    @mock.patch('data_gathering_subsystem.data_modules.locations.locations.BytesIO')
    @mock.patch('zipfile.ZipFile')
    @mock.patch('requests.get')
    @mock.patch('data_gathering_subsystem.data_modules.locations.locations.MongoDBCollection')
    def test_correct_data_collection_all_found_no_unmatched_no_multiple(self, mock_collection, mock_requests,
                                                                        mock_zipfile, mock_bytes):
        # Mocking ZipFile
        mock_zipfile.return_value = Mock()
        mock_zipfile.return_value.open.return_value = BytesIO(DATA)
        mock_zipfile.return_value.infolist.return_value = [ZipInfo('cities1000.txt', (2018, 1, 2, 2, 13, 24))]
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.find.return_value = ([], None)
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 5, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        side_effect = [dumps(x) for x in [{"RESULTS": [
            {"name": "Kabul, Afghanistan", "type": "city", "c": "AF", "zmw": "00000.551.40948", "tz": "Asia/Kabul",
             "tzs": "+0430", "l": "/q/zmw:00000.551.40948", "ll": "34.529999 69.169998", "lat": "34.529999",
             "lon": "69.169998"}]}, {"status": "ok", "data": [
            {"uid": 1234, "aqi": "744", "time": {"tz": "+0530", "stime": "2018-01-02 21:00:00", "vtime": 1514907000},
             "station": {"name": "Kabul, Afghanistan", "geo": [34.52813, 69.17233], "url": "kabul/afghanistan"}}]}, {
            "RESULTS": [
                {"name": "Cairo, Egypt", "type": "city", "c": "EG", "zmw": "00000.1.62375", "tz": "Africa/Cairo",
                 "tzs": "EET", "l": "/q/zmw:00000.1.62375", "ll": "30.059999 31.250000", "lat": "30.059999",
                 "lon": "31.250000"}]}, {"status": "ok", "data": [
            {"uid": 2390, "aqi": "983", "time": {"tz": "+0530", "stime": "2018-01-02 21:00:00", "vtime": 1514907000},
             "station": {"name": "Cairo, Egypt", "geo": [30.06263, 31.24967], "url": "cairo/egypt"}}]}, {"RESULTS": [
            {"name": "Guatemala City, Guatemala", "type": "city", "c": "GT", "zmw": "00000.1.78641",
             "tz": "America/Guatemala", "tzs": "CST", "l": "/q/zmw:00000.1.78641", "ll": "14.580000 -90.519997",
             "lat": "14.580000", "lon": "-90.519997"}]}, {"status": "ok", "data": [
            {"uid": 4523, "aqi": "442", "time": {"tz": "+0530", "stime": "2018-01-02 21:00:00", "vtime": 1514907000},
             "station": {"name": "Guatemala City, Guatemala", "geo": [14.64072, -90.51327],
                         "url": "gcity/guatemala"}}]}, {"RESULTS": [
            {"name": "Delhi, India", "type": "city", "c": "IN", "zmw": "00000.56.42182", "tz": "Asia/Kolkata",
             "tzs": "IST", "l": "/q/zmw:00000.56.42182", "ll": "28.660000 77.230003", "lat": "28.660000",
             "lon": "77.230003"}]}, {"status": "ok", "data": [
            {"uid": 2556, "aqi": "744", "time": {"tz": "+0530", "stime": "2018-01-02 21:00:00", "vtime": 1514907000},
             "station": {"name": "R.K. Puram, Delhi, Delhi, India", "geo": [28.5651095, 77.1752543],
                         "url": "delhi/r.k.-puram"}}]}, {"RESULTS": [
            {"name": "Mexico City, Mexico", "type": "city", "c": "MX", "zmw": "00000.50.76679",
             "tz": "America/Mexico_City", "tzs": "CST", "l": "/q/zmw:00000.50.76679", "ll": "19.430000 -99.139999",
             "lat": "19.430000", "lon": "-99.139999"}]}, {"status": "ok", "data": [
            {"uid": 7618, "aqi": "611", "time": {"tz": "+0530", "stime": "2018-01-02 21:00:00", "vtime": 1514907000},
             "station": {"name": "Mexico City, Mexico", "geo": [21.42847, -97.12766], "url": "mexico/mexico"}}]}]]
        side_effect.append(
                'HDR\n1273294	Delhi	28.666668	77.216667	IN\n261481	New Delhi	28.612820	77.231140	IN\n530597	Mexico City	19.428471	-99.127663	MX\n138958	Kabul	34.528130	69.172333	AF\n598132	Guatemala City	14.640720	-90.513268	GT\n60630	Cairo	30.062630	31.249670	EG\n')
        response.content.decode = Mock(side_effect=side_effect)
        # Actual execution
        self.data_collector = locations.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.config['LOCATIONS'] = LOCATIONS
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_requests.called)
        self.assertTrue(mock_zipfile.called)
        self.assertTrue(mock_bytes.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertFalse(self.data_collector.config['LOCATIONS']['Kabul']['missing'])
        self.assertFalse(self.data_collector.config['LOCATIONS']['Mexico City']['missing'])
        self.assertFalse(self.data_collector.config['LOCATIONS']['Guatemala City']['missing'])
        self.assertFalse(self.data_collector.config['LOCATIONS']['Delhi']['missing'])
        self.assertFalse(self.data_collector.config['LOCATIONS']['Cairo']['missing'])
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(5, self.data_collector.state['data_elements'])
        self.assertEqual(5, self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['MAX_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('data_gathering_subsystem.data_modules.locations.locations.BytesIO')
    @mock.patch('zipfile.ZipFile')
    @mock.patch('requests.get')
    @mock.patch('data_gathering_subsystem.data_modules.locations.locations.MongoDBCollection')
    def test_correct_data_collection_all_found_unmatched_multiple(self, mock_collection, mock_requests, mock_zipfile,
                                                                  mock_bytes):
        # Mocking ZipFile
        mock_zipfile.return_value = Mock()
        mock_zipfile.return_value.open.return_value = BytesIO(DATA)
        mock_zipfile.return_value.infolist.return_value = [ZipInfo('cities1000.txt', (2018, 1, 2, 2, 13, 24))]
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.find.return_value = ([], None)
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 5, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        side_effect = [dumps(x) for x in [{"RESULTS": [
            {"name": "Kabul, Afghanistan", "type": "city", "c": "AF", "zmw": "00000.551.40948", "tz": "Asia/Kabul",
             "tzs": "+0430", "l": "/q/zmw:00000.551.40948", "ll": "34.529999 69.169998", "lat": "34.529999",
             "lon": "69.169998"},
            {"name": "Kabul, Afghanistan", "type": "city", "c": "AF", "zmw": "00000.551.40948", "tz": "Asia/Kabul",
             "tzs": "+0430", "l": "/q/zmw:00000.551.40948", "ll": "34.529999 69.169998", "lat": "34.529999",
             "lon": "69.169998"}]}, {"status": "ok", "data": [
            {"uid": 1234, "aqi": "744", "time": {"tz": "+0530", "stime": "2018-01-02 21:00:00", "vtime": 1514907000},
             "station": {"name": "Kabul, Afghanistan", "geo": [34.52813, 69.17233], "url": "kabul/afghanistan"}},
            {"uid": 1234, "aqi": "744", "time": {"tz": "+0530", "stime": "2018-01-02 21:00:00", "vtime": 1514907000},
             "station": {"name": "Kabul, Afghanistan", "geo": [34.52813, 69.17233], "url": "kabul/afghanistan"}}]}, {
            "RESULTS": [
                {"name": "Cairo, Egypt", "type": "city", "c": "EG", "zmw": "00000.1.62375", "tz": "Africa/Cairo",
                 "tzs": "EET", "l": "/q/zmw:00000.1.62375", "ll": "30.059999 31.250000", "lat": "30.059999",
                 "lon": "31.250000"}]}, {"status": "ok", "data": [
            {"uid": 2390, "aqi": "983", "time": {"tz": "+0530", "stime": "2018-01-02 21:00:00", "vtime": 1514907000},
             "station": {"name": "Cairo, Egypt", "geo": [30.06263, 31.24967], "url": "cairo/egypt"}}]}, {"RESULTS": [
            {"name": "Guatemala City, Guatemala", "type": "city", "c": "GT", "zmw": "00000.1.78641",
             "tz": "America/Guatemala", "tzs": "CST", "l": "/q/zmw:00000.1.78641", "ll": "14.580000 -90.519997",
             "lat": "14.580000", "lon": "-90.519997"}]}, {"status": "ok", "data": [
            {"uid": 4523, "aqi": "442", "time": {"tz": "+0530", "stime": "2018-01-02 21:00:00", "vtime": 1514907000},
             "station": {"name": "Guatemala City, Guatemala", "geo": [14.64072, -90.51327],
                         "url": "gcity/guatemala"}}]}, {"RESULTS": [
            {"name": "Delhi, India", "type": "city", "c": "IN", "zmw": "00000.56.42182", "tz": "Asia/Kolkata",
             "tzs": "IST", "l": "/q/zmw:00000.56.42182", "ll": "28.660000 77.230003", "lat": "28.660000",
             "lon": "77.230003"}]}, {"status": "ok", "data": [
            {"uid": 2556, "aqi": "744", "time": {"tz": "+0530", "stime": "2018-01-02 21:00:00", "vtime": 1514907000},
             "station": {"name": "R.K. Puram, Delhi, Delhi, India", "geo": [28.5651095, 77.1752543],
                         "url": "delhi/r.k.-puram"}}]}, {"RESULTS": [
            {"name": "Mexico City, Mexico", "type": "city", "c": "MX", "zmw": "00000.50.76679",
             "tz": "America/Mexico_City", "tzs": "CST", "l": "/q/zmw:00000.50.76679", "ll": "19.430000 -99.139999",
             "lat": "19.430000", "lon": "-99.139999"}]}, {"status": "ok", "data": [
            {"uid": 7618, "aqi": "611", "time": {"tz": "+0530", "stime": "2018-01-02 21:00:00", "vtime": 1514907000},
             "station": {"name": "Mexico City, Mexico", "geo": [21.42847, -97.12766], "url": "mexico/mexico"}}]}]]
        side_effect.append(
                'HDR\n1273294	Delhi	100.666668	75.216667	IN\n261481	New Delhi	25.612820	75.231140	IN\n530597	Mexico City	1.428471	-21.127663	MX\n138958	Kabul	34.528130	69.172333	AF\n598132	Guatemala City	14.640720	-90.513268	GT\n60630	Cairo	30.062630	31.249670	EG\n')
        response.content.decode = Mock(side_effect=side_effect)
        # Actual execution
        self.data_collector = locations.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.config['LOCATIONS'] = LOCATIONS
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_requests.called)
        self.assertTrue(mock_zipfile.called)
        self.assertTrue(mock_bytes.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertFalse(self.data_collector.config['LOCATIONS']['Kabul']['missing'])
        self.assertFalse(self.data_collector.config['LOCATIONS']['Mexico City']['missing'])
        self.assertFalse(self.data_collector.config['LOCATIONS']['Guatemala City']['missing'])
        self.assertFalse(self.data_collector.config['LOCATIONS']['Delhi']['missing'])
        self.assertFalse(self.data_collector.config['LOCATIONS']['Cairo']['missing'])
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(5, self.data_collector.state['data_elements'])
        self.assertEqual(5, self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['MAX_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('data_gathering_subsystem.data_modules.locations.locations.BytesIO')
    @mock.patch('zipfile.ZipFile')
    @mock.patch('requests.get')
    @mock.patch('data_gathering_subsystem.data_modules.locations.locations.MongoDBCollection')
    def test_correct_data_collection_some_locations_not_found(self, mock_collection, mock_requests, mock_zipfile,
                                                              mock_bytes):
        # Mocking ZipFile
        mock_zipfile.return_value = Mock()
        data = DATA[:]
        data = "360630	Cairo	Cairo	Al Qahirah,Al Qāhirah,CAI,Caire,Cairo,Cairo - alqahrt,Cairo - القاهرة,Cairu,Cairus,Caïro,El Caire,El Cairo,El Kahira,El Kahirah,El-Qahira,El-Qâhira,Il Cairo,Kaherah,Kahira,Kahirae,Kahire,Kahirä,Kair,Kaira,Kairas,Kairo,Kairó,Kajro,Kayro,Kaíró,Kaïro,Káhira,Le Caire,Lo Cayiro,Lungsod ng Cairo,Masr,Misr,Qahirə,alqahrt,kai luo,kailo,kairo,keyro,khiro,qahrh,qhyr,Ël Cairo,Ël Càiro,Κάιρο,Каир,Каиро,Кайро,Каїр,קהיר,القاهرة,قاهره,قاھىرە,قاہرہ,கெய்ரோ,ไคโร,ཁ་ཡི་རོ,ქაირო,ካይሮ,カイロ,开罗,카이로	30.06263	31.24967	P	PPLC	EG		11				7734614		23	Africa/Cairo	2015-06-03\n" + "3598132	Guatemala City	Guatemala City	Cidade da Guatemala,Citta del Guatemala,Città del Guatemala,Ciudad Guatemala,Ciudad de Guatemala,Ciutat de Guatemala,GUA,Guate,Guatemala,Guatemala City,Guatemala Hiria,Guatemala by,Guatemala la Nueva,Guatemala-Stadt,Guatemala-Urbo,Guatemala-stad,Gvatemala,Gvatemalurbo,Gwatemala,New Guatemala,Nueva Guatemala,Nueva Guatemala de la Asuncion,Nueva Guatemala de la Asunción,Pole tes Gouatemalas,Santiago de Guatimala,gua de ma la shi,guatemarashiti,gwatemalla si,gwatemallasiti,kawtemalasiti,mdynt ghwatymala,shhr gwatmala,Πόλη της Γουατεμάλας,Гватемала,גואטמלה סיטי,גוואטמלה סיטי,شهر گواتمالا,مدينة غواتيمالا,กัวเตมาลาซิตี,グアテマラシティ,瓜地馬拉市,과테말라 시,과테말라시티	14.64072	-90.51327	P	PPLC	GT		07				994938		1508	America/Guatemala	2017-06-20\n" + "1273294	Delhi	Delhi	DEL,Daehli,Dehli,Dehlī,Delchi,Delhi,Delhio,Delhí,Delhî,Deli,Delis,Delkhi,Dellium,Delí,Dilhi,Dilli,Dillí,Dillī,Dähli,Déhli,Faritani Delhi,Gorad Dehli,New Delhi,Old Delhi,Sahdzahanabad,Stare Deli,de li,dehali,deli,delli,deri,dhilli,dhly,dhly qdym,dil'hi,dili,dilli,dlhy,dly,dlھy,dylhy,na'i dilli,prany dہly,tilli,Šáhdžahanabád,Δελχί,Горад Дэлі,Дели,Делхи,Делі,Деҳли,Старе Делі,Դելի,דלהי,דעלהי,دلهي,دلھی,دلی,دهلي,دهلی قدیم,ديلهى,دہلی,دێھلی,پرانی دہلی,ډېلي,ދިއްލީ,दिल्ली,देहली,नई दिल्ली,দিল্লি,দিল্লী,ਦਿੱਲੀ,દિલ્હી,ଦିଲ୍ଲୀ,தில்லி,ఢిల్లీ,ದೆಹಲಿ,ഡെൽഹി,เดลี,დელი,デリー,德里,델리	28.65195	77.23149	P	PPLA	IN		07				10927986		227	Asia/Kolkata	2017-10-30\n" + "3530597	Mexico City	Mexico City	Cidade de Mexico,Cidade de México,Cidade do Mexico,Cidade do México,Cita du Messicu,Citta del Messico,Città del Messico,Cità dû Messicu,Cità dû Mèssicu,Ciudad Mexico,Ciudad de Mejico,Ciudad de Mexico,Ciudad de Méjico,Ciudad de México,Ciutat de Mexic,Ciutat de Mèxic,Lungsod ng Mexico,Lungsod ng México,MEX,Mehiko,Mekhiko,Meksikas,Meksiko,Meksiko Siti,Meksikurbo,Meksyk,Mexico,Mexico City,Mexico D.F.,Mexico DF,Mexico Distrito Federal,Mexico by,Mexico-stad,Mexicopolis,Mexiko,Mexiko Hiria,Mexiko-Stadt,Mexikoborg,Mexíkóborg,México,México Distrito Federal,Nkoyo,Pole tou Mexikou,Valle de Mexico,Valle de México,mdynt mksykw,megsiko si,megsikositi,mekishikoshiti,meksiko siti,meksikositi,mkzykw,mkzykwsyty,mo xi ge cheng,mqsyqw syty,Πόλη του Μεξικού,Мексико,Мексико Сити,Мехико,Мехіко,מקסיקו סיטי,مدينة مكسيكو,مکزیکو,مکزیکوسیتی,مېكسىكا شەھىرى,मेक्सिको सिटी,เม็กซิโกซิตี,მეხიკო,メキシコシティ,墨西哥城,멕시코 시,멕시코시티	19.42847	-99.12766	P	PPLC	MX		09	015			12294193		2240	America/Mexico_City	2017-06-22\n"
        data = data.encode()
        mock_zipfile.return_value.open.return_value = BytesIO(data)
        mock_zipfile.return_value.infolist.return_value = [ZipInfo('cities1000.txt', (2018, 1, 2, 2, 13, 24))]
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.find.return_value = ([], None)
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 4, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        side_effect = [dumps(x) for x in [{"RESULTS": [
            {"name": "Cairo, Egypt", "type": "city", "c": "EG", "zmw": "00000.1.62375", "tz": "Africa/Cairo",
             "tzs": "EET", "l": "/q/zmw:00000.1.62375", "ll": "30.059999 31.250000", "lat": "30.059999",
             "lon": "31.250000"}]}, {"status": "ok", "data": [
            {"uid": 2390, "aqi": "983", "time": {"tz": "+0530", "stime": "2018-01-02 21:00:00", "vtime": 1514907000},
             "station": {"name": "Cairo, Egypt", "geo": [30.06263, 31.24967], "url": "cairo/egypt"}}]}, {"RESULTS": [
            {"name": "Guatemala City, Guatemala", "type": "city", "c": "GT", "zmw": "00000.1.78641",
             "tz": "America/Guatemala", "tzs": "CST", "l": "/q/zmw:00000.1.78641", "ll": "14.580000 -90.519997",
             "lat": "14.580000", "lon": "-90.519997"}]}, {"status": "ok", "data": [
            {"uid": 4523, "aqi": "442", "time": {"tz": "+0530", "stime": "2018-01-02 21:00:00", "vtime": 1514907000},
             "station": {"name": "Guatemala City, Guatemala", "geo": [14.64072, -90.51327],
                         "url": "gcity/guatemala"}}]}, {"RESULTS": [
            {"name": "Delhi, India", "type": "city", "c": "IN", "zmw": "00000.56.42182", "tz": "Asia/Kolkata",
             "tzs": "IST", "l": "/q/zmw:00000.56.42182", "ll": "28.660000 77.230003", "lat": "28.660000",
             "lon": "77.230003"}]}, {"status": "ok", "data": [
            {"uid": 2556, "aqi": "744", "time": {"tz": "+0530", "stime": "2018-01-02 21:00:00", "vtime": 1514907000},
             "station": {"name": "R.K. Puram, Delhi, Delhi, India", "geo": [28.5651095, 77.1752543],
                         "url": "delhi/r.k.-puram"}}]}, {"RESULTS": [
            {"name": "Mexico City, Mexico", "type": "city", "c": "MX", "zmw": "00000.50.76679",
             "tz": "America/Mexico_City", "tzs": "CST", "l": "/q/zmw:00000.50.76679", "ll": "19.430000 -99.139999",
             "lat": "19.430000", "lon": "-99.139999"}]}, {"status": "ok", "data": [
            {"uid": 7618, "aqi": "611", "time": {"tz": "+0530", "stime": "2018-01-02 21:00:00", "vtime": 1514907000},
             "station": {"name": "Mexico City, Mexico", "geo": [21.42847, -97.12766], "url": "mexico/mexico"}}]}]]
        side_effect.append(
                'HDR\n1273294	Delhi	28.666668	77.216667	IN\n261481	New Delhi	28.612820	77.231140	IN\n530597	Mexico City	19.428471	-99.127663	MX\n598132	Guatemala City	14.640720	-90.513268	GT\n60630	Cairo	30.062630	31.249670	EG\n')
        response.content.decode = Mock(side_effect=side_effect)
        # Actual execution
        self.data_collector = locations.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.config['LOCATIONS'] = LOCATIONS
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_requests.called)
        self.assertTrue(mock_zipfile.called)
        self.assertTrue(mock_bytes.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertTrue(self.data_collector.config['LOCATIONS']['Kabul']['missing'])
        self.assertFalse(self.data_collector.config['LOCATIONS']['Mexico City']['missing'])
        self.assertFalse(self.data_collector.config['LOCATIONS']['Guatemala City']['missing'])
        self.assertFalse(self.data_collector.config['LOCATIONS']['Delhi']['missing'])
        self.assertFalse(self.data_collector.config['LOCATIONS']['Cairo']['missing'])
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(4, self.data_collector.state['data_elements'])
        self.assertEqual(4, self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['MAX_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('data_gathering_subsystem.data_modules.locations.locations.BytesIO')
    @mock.patch('zipfile.ZipFile')
    @mock.patch('requests.get')
    def test_correct_data_collection_no_updated(self, mock_requests, mock_zipfile, mock_bytes):
        # Mocking ZipFile
        mock_zipfile.return_value = Mock()
        mock_zipfile.return_value.open.return_value = BytesIO(DATA)
        mock_zipfile.return_value.infolist.return_value = [ZipInfo('cities1000.txt', (2018, 1, 2, 2, 13, 24))]
        # Mocking requests (get and response content)
        mock_requests.return_value = Mock()
        # Actual execution
        self.data_collector = locations.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.config['LOCATIONS'] = LOCATIONS
        self.data_collector.config['STATE_STRUCT']['last_modified'] = '2018-01-02T02:13:24.0001Z'
        self.data_collector.run()
        self.assertTrue(mock_requests.called)
        self.assertTrue(mock_zipfile.called)
        self.assertTrue(mock_bytes.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(0, self.data_collector.state['data_elements'])
        self.assertEqual(0, self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['MIN_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('data_gathering_subsystem.data_modules.locations.locations.BytesIO')
    @mock.patch('zipfile.ZipFile')
    @mock.patch('requests.get')
    @mock.patch('data_gathering_subsystem.data_modules.locations.locations.MongoDBCollection')
    def test_correct_data_collection_not_all_collected(self, mock_collection, mock_requests, mock_zipfile, mock_bytes):
        # Mocking ZipFile
        mock_zipfile.return_value = Mock()
        mock_zipfile.return_value.open.return_value = BytesIO(DATA)
        mock_zipfile.return_value.infolist.return_value = [ZipInfo('cities1000.txt', (2018, 1, 2, 2, 13, 24))]
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.find.return_value = ([], None)
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 3, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        side_effect = [dumps(x) for x in [{"RESULTS": [
            {"name": "Kabul, Afghanistan", "type": "city", "c": "AF", "zmw": "00000.551.40948", "tz": "Asia/Kabul",
             "tzs": "+0430", "l": "/q/zmw:00000.551.40948", "ll": "34.529999 69.169998", "lat": "34.529999",
             "lon": "69.169998"}]}, {"status": "ok", "data": [
            {"uid": 1234, "aqi": "744", "time": {"tz": "+0530", "stime": "2018-01-02 21:00:00", "vtime": 1514907000},
             "station": {"name": "Kabul, Afghanistan", "geo": [34.52813, 69.17233], "url": "kabul/afghanistan"}}]}, {
            "RESULTS": [
                {"name": "Cairo, Egypt", "type": "city", "c": "EG", "zmw": "00000.1.62375", "tz": "Africa/Cairo",
                 "tzs": "EET", "l": "/q/zmw:00000.1.62375", "ll": "30.059999 31.250000", "lat": "30.059999",
                 "lon": "31.250000"}]}, {"status": "ok", "data": [
            {"uid": 2390, "aqi": "983", "time": {"tz": "+0530", "stime": "2018-01-02 21:00:00", "vtime": 1514907000},
             "station": {"name": "Cairo, Egypt", "geo": [30.06263, 31.24967], "url": "cairo/egypt"}}]}, {"RESULTS": [
            {"name": "Guatemala City, Guatemala", "type": "city", "c": "GT", "zmw": "00000.1.78641",
             "tz": "America/Guatemala", "tzs": "CST", "l": "/q/zmw:00000.1.78641", "ll": "14.580000 -90.519997",
             "lat": "14.580000", "lon": "-90.519997"}]}, {"status": "ok", "data": [
            {"uid": 4523, "aqi": "442", "time": {"tz": "+0530", "stime": "2018-01-02 21:00:00", "vtime": 1514907000},
             "station": {"name": "Guatemala City, Guatemala", "geo": [14.64072, -90.51327],
                         "url": "gcity/guatemala"}}]}, {"RESULTS": [
            {"name": "Delhi, India", "type": "city", "c": "IN", "zmw": "00000.56.42182", "tz": "Asia/Kolkata",
             "tzs": "IST", "l": "/q/zmw:00000.56.42182", "ll": "28.660000 77.230003", "lat": "25.660000",
             "lon": "77.230003"}]}, {"status": "ok", "data": [
            {"uid": 2556, "aqi": "744", "time": {"tz": "+0530", "stime": "2018-01-02 21:00:00", "vtime": 1514907000},
             "station": {"name": "R.K. Puram, Delhi, Delhi, India", "geo": [28.5651095, 77.1752543],
                         "url": "delhi/r.k.-puram"}}]}, {"RESULTS": [
            {"name": "Mexico City, Mexico", "type": "city", "c": "MX", "zmw": "00000.50.76679",
             "tz": "America/Mexico_City", "tzs": "CST", "l": "/q/zmw:00000.50.76679", "ll": "19.430000 -99.139999",
             "lat": "19.430000", "lon": "-99.139999"}]}, {"status": "ok", "data": [
            {"uid": 7618, "aqi": "611", "time": {"tz": "+0530", "stime": "2018-01-02 21:00:00", "vtime": 1514907000},
             "station": {"name": "Mexico City, Mexico", "geo": [21.42847, -97.12766], "url": "mexico/mexico"}}]}]]
        side_effect.append(
                'HDR\n1273294	Delhi	28.666668	77.216667	IN\n261481	New Delhi	28.612820	77.231140	IN\n530597	Mexico City	19.428471	-99.127663	MX\n138958	Kabul	34.528130	69.172333	AF\n598132	Guatemala City	14.640720	-90.513268	GT\n60630	Cairo	30.062630	31.249670	EG\n')
        response.content.decode = Mock(side_effect=side_effect)
        # Actual execution
        self.data_collector = locations.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.config['LOCATIONS'] = LOCATIONS
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_requests.called)
        self.assertTrue(mock_zipfile.called)
        self.assertTrue(mock_bytes.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertFalse(self.data_collector.config['LOCATIONS']['Kabul']['missing'])
        self.assertFalse(self.data_collector.config['LOCATIONS']['Mexico City']['missing'])
        self.assertFalse(self.data_collector.config['LOCATIONS']['Guatemala City']['missing'])
        self.assertFalse(self.data_collector.config['LOCATIONS']['Delhi']['missing'])
        self.assertFalse(self.data_collector.config['LOCATIONS']['Cairo']['missing'])
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(5, self.data_collector.state['data_elements'])
        self.assertEqual(3, self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['MAX_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('data_gathering_subsystem.data_modules.locations.locations.BytesIO')
    @mock.patch('zipfile.ZipFile')
    @mock.patch('requests.get')
    @mock.patch('data_gathering_subsystem.data_modules.locations.locations.MongoDBCollection')
    def test_data_collection_with_invalid_data_from_server(self, mock_collection, mock_requests, mock_zipfile,
                                                           mock_bytes):
        # Mocking ZipFile
        mock_zipfile.return_value = Mock()
        mock_zipfile.return_value.open.return_value = BytesIO(DATA)
        mock_zipfile.return_value.infolist.return_value = [ZipInfo('cities1000.txt', (2018, 1, 2, 2, 13, 24))]
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.find.return_value = ([], None)
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 5, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        side_effect = [dumps(x) for x in [{"RESULTS": [
            {"name": "Kabul, Afghanistan", "type": "city", "c": "AF", "zmw": "00000.551.40948", "tz": "Asia/Kabul",
             "tzs": "+0430", "l": "/q/zmw:00000.551.40948", "ll": "34.529999 69.169998", "lat": "34.529999",
             "lon": "69.169998"}]}, {"status":"ok","data":['invalid']}, {
            "RESULTS": [
                {"name": "Cairo, Egypt", "type": "city", "c": "EG", "zmw": "00000.1.62375", "tz": "Africa/Cairo",
                 "tzs": "EET", "l": "/q/zmw:00000.1.62375", "ll": "30.059999 31.250000", "lat": "30.059999",
                 "lon": "31.250000"}]}, {"status": "ok", "data": [
            {"uid": 2390, "aqi": "983", "time": {"tz": "+0530", "stime": "2018-01-02 21:00:00", "vtime": 1514907000},
             "station": {"name": "Cairo, Egypt", "geo": [30.06263, 31.24967], "url": "cairo/egypt"}}]}, {"RESULTS": [
            {"name": "Guatemala City, Guatemala", "type": "city", "c": "GT", "zmw": "00000.1.78641",
             "tz": "America/Guatemala", "tzs": "CST", "l": "/q/zmw:00000.1.78641", "ll": "14.580000 -90.519997",
             "lat": "14.580000", "lon": "-90.519997"}]}, {"status": "ok", "data": [
            {"uid": 4523, "aqi": "442", "time": {"tz": "+0530", "stime": "2018-01-02 21:00:00", "vtime": 1514907000},
             "station": {"name": "Guatemala City, Guatemala", "geo": [14.64072, -90.51327],
                         "url": "gcity/guatemala"}}]}, {"RESULTS": [
            {"name": "Delhi, India", "type": "city", "c": "IN", "zmw": "00000.56.42182", "tz": "Asia/Kolkata",
             "tzs": "IST", "l": "/q/zmw:00000.56.42182", "ll": "28.660000 77.230003", "lat": "",
             "lon": ""}]}, {"status": "ok", "data": [
            {"uid": 2556, "aqi": "744", "time": {"tz": "+0530", "stime": "2018-01-02 21:00:00", "vtime": 1514907000},
             "station": {"name": "R.K. Puram, Delhi, Delhi, India", "geo": [28.5651095, 77.1752543],
                         "url": "delhi/r.k.-puram"}}]}, {"RESULTS": [
            {"name": "Mexico City, Mexico", "type": "city", "c": "MX", "zmw": "00000.50.76679",
             "tz": "America/Mexico_City", "tzs": "CST", "l": "/q/zmw:00000.50.76679", "ll": "19.430000 -99.139999",
             "lat": "19.430000", "lon": "-99.139999"}]}, {"status": "ok", "data": [
            {"uid": 7618, "aqi": "611", "time": {"tz": "+0530", "stime": "2018-01-02 21:00:00", "vtime": 1514907000},
             "station": {"name": "Mexico City, Mexico", "geo": [21.42847, -97.12766], "url": "mexico/mexico"}}]}]]
        side_effect.append(
                'HDR\n1273294	Delhi	28.666668	77.216667	IN\n261481	New Delhi	28.612820	77.231140	IN\n530597	Mexico City	19.428471	-99.127663	MX\n138958	Kabul	34.528130	69.172333	AF\n598132	Guatemala City	14.640720	-90.513268	GT\n60630	Cairo	30.062630	31.249670	EG\n')
        response.content.decode = Mock(side_effect=side_effect)
        # Actual execution
        self.data_collector = locations.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.config['LOCATIONS'] = LOCATIONS
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_requests.called)
        self.assertTrue(mock_zipfile.called)
        self.assertTrue(mock_bytes.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertFalse(self.data_collector.config['LOCATIONS']['Kabul']['missing'])
        self.assertFalse(self.data_collector.config['LOCATIONS']['Mexico City']['missing'])
        self.assertFalse(self.data_collector.config['LOCATIONS']['Guatemala City']['missing'])
        self.assertFalse(self.data_collector.config['LOCATIONS']['Delhi']['missing'])
        self.assertFalse(self.data_collector.config['LOCATIONS']['Cairo']['missing'])
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(5, self.data_collector.state['data_elements'])
        self.assertEqual(5, self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['MAX_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('data_gathering_subsystem.data_modules.locations.locations.BytesIO')
    @mock.patch('zipfile.ZipFile')
    @mock.patch('requests.get')
    @mock.patch('data_gathering_subsystem.data_modules.locations.locations.MongoDBCollection')
    def test_correct_data_collection_no_elements_collected(self, mock_collection, mock_requests, mock_zipfile,
                                                           mock_bytes):
        # Mocking ZipFile
        mock_zipfile.return_value = Mock()
        mock_zipfile.return_value.open.return_value = BytesIO(DATA)
        mock_zipfile.return_value.infolist.return_value = [ZipInfo('cities1000.txt', (2018, 1, 2, 2, 13, 24))]
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.find.return_value = ([], None)
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 0, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        side_effect = [dumps(x) for x in [{"RESULTS": [
            {"name": "Kabul, Afghanistan", "type": "city", "c": "AF", "zmw": "00000.551.40948", "tz": "Asia/Kabul",
             "tzs": "+0430", "l": "/q/zmw:00000.551.40948", "ll": "34.529999 69.169998", "lat": "34.529999",
             "lon": "69.169998"}]}, {"status": "ok", "data": [
            {"uid": 1234, "aqi": "744", "time": {"tz": "+0530", "stime": "2018-01-02 21:00:00", "vtime": 1514907000},
             "station": {"name": "Kabul, Afghanistan", "geo": [34.52813, 69.17233], "url": "kabul/afghanistan"}}]}, {
            "RESULTS": [
                {"name": "Cairo, Egypt", "type": "city", "c": "EG", "zmw": "00000.1.62375", "tz": "Africa/Cairo",
                 "tzs": "EET", "l": "/q/zmw:00000.1.62375", "ll": "30.059999 31.250000", "lat": "30.059999",
                 "lon": "31.250000"}]}, {"status": "ok", "data": [
            {"uid": 2390, "aqi": "983", "time": {"tz": "+0530", "stime": "2018-01-02 21:00:00", "vtime": 1514907000},
             "station": {"name": "Cairo, Egypt", "geo": [30.06263, 31.24967], "url": "cairo/egypt"}}]}, {"RESULTS": [
            {"name": "Guatemala City, Guatemala", "type": "city", "c": "GT", "zmw": "00000.1.78641",
             "tz": "America/Guatemala", "tzs": "CST", "l": "/q/zmw:00000.1.78641", "ll": "14.580000 -90.519997",
             "lat": "14.580000", "lon": "-90.519997"}]}, {"status": "ok", "data": [
            {"uid": 4523, "aqi": "442", "time": {"tz": "+0530", "stime": "2018-01-02 21:00:00", "vtime": 1514907000},
             "station": {"name": "Guatemala City, Guatemala", "geo": [14.64072, -90.51327],
                         "url": "gcity/guatemala"}}]}, {"RESULTS": [
            {"name": "Delhi, India", "type": "city", "c": "IN", "zmw": "00000.56.42182", "tz": "Asia/Kolkata",
             "tzs": "IST", "l": "/q/zmw:00000.56.42182", "ll": "28.660000 77.230003", "lat": "28.660000",
             "lon": "77.230003"}]}, {"status": "ok", "data": [
            {"uid": 2556, "aqi": "744", "time": {"tz": "+0530", "stime": "2018-01-02 21:00:00", "vtime": 1514907000},
             "station": {"name": "R.K. Puram, Delhi, Delhi, India", "geo": [28.5651095, 77.1752543],
                         "url": "delhi/r.k.-puram"}}]}, {"RESULTS": [
            {"name": "Mexico City, Mexico", "type": "city", "c": "MX", "zmw": "00000.50.76679",
             "tz": "America/Mexico_City", "tzs": "CST", "l": "/q/zmw:00000.50.76679", "ll": "19.430000 -99.139999",
             "lat": "19.430000", "lon": "-99.139999"}]}, {"status": "ok", "data": [
            {"uid": 7618, "aqi": "611", "time": {"tz": "+0530", "stime": "2018-01-02 21:00:00", "vtime": 1514907000},
             "station": {"name": "Mexico City, Mexico", "geo": [21.42847, -97.12766], "url": "mexico/mexico"}}]}]]
        side_effect.append(
                'HDR\n1273294	Delhi	28.666668	77.216667	IN\n261481	New Delhi	28.612820	77.231140	IN\n530597	Mexico City	19.428471	-99.127663	MX\n138958	Kabul	34.528130	69.172333	AF\n598132	Guatemala City	14.640720	-90.513268	GT\n60630	Cairo	30.062630	31.249670	EG\n')
        response.content.decode = Mock(side_effect=side_effect)
        # Actual execution
        self.data_collector = locations.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.config['LOCATIONS'] = LOCATIONS
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_requests.called)
        self.assertTrue(mock_zipfile.called)
        self.assertTrue(mock_bytes.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertFalse(self.data_collector.successful_execution())
        self.assertFalse(self.data_collector.config['LOCATIONS']['Kabul']['missing'])
        self.assertFalse(self.data_collector.config['LOCATIONS']['Mexico City']['missing'])
        self.assertFalse(self.data_collector.config['LOCATIONS']['Guatemala City']['missing'])
        self.assertFalse(self.data_collector.config['LOCATIONS']['Delhi']['missing'])
        self.assertFalse(self.data_collector.config['LOCATIONS']['Cairo']['missing'])
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(5, self.data_collector.state['data_elements'])
        self.assertEqual(0, self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['MAX_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('data_gathering_subsystem.data_modules.locations.locations.BytesIO')
    @mock.patch('zipfile.ZipFile')
    @mock.patch('requests.get')
    @mock.patch('data_gathering_subsystem.data_modules.locations.locations.MongoDBCollection')
    def test_correct_data_collection_missing_locations_in_database(self, mock_collection, mock_requests, mock_zipfile,
                                                           mock_bytes):
        # Mocking ZipFile
        mock_zipfile.return_value = Mock()
        mock_zipfile.return_value.open.return_value = BytesIO(DATA)
        mock_zipfile.return_value.infolist.return_value = [ZipInfo('cities1000.txt', (2018, 1, 2, 2, 13, 24))]
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.find.return_value = ([{'name': 'Delhi'}, {'name': 'Mexico City'},
                {'name': 'Guatemala City'}, {'name': 'Cairo'}], None)
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 1, 'nMatched': 0, 'nUpserted': 0}
        # Mocking requests (get and response content)
        mock_requests.return_value = response = Mock()
        side_effect = [dumps(x) for x in [{"RESULTS": [
            {"name": "Kabul, Afghanistan", "type": "city", "c": "AF", "zmw": "00000.551.40948", "tz": "Asia/Kabul",
             "tzs": "+0430", "l": "/q/zmw:00000.551.40948", "ll": "34.529999 69.169998", "lat": "34.529999",
             "lon": "69.169998"}]}, {"status": "ok", "data": [
            {"uid": 1234, "aqi": "744", "time": {"tz": "+0530", "stime": "2018-01-02 21:00:00", "vtime": 1514907000},
             "station": {"name": "Kabul, Afghanistan", "geo": [34.52813, 69.17233], "url": "kabul/afghanistan"}}]}]]
        side_effect.append(
                'HDR\n1273294	Delhi	28.666668	77.216667	IN\n261481	New Delhi	28.612820	77.231140	IN\n530597	Mexico City	19.428471	-99.127663	MX\n138958	Kabul	34.528130	69.172333	AF\n598132	Guatemala City	14.640720	-90.513268	GT\n60630	Cairo	30.062630	31.249670	EG\n')
        response.content.decode = Mock(side_effect=side_effect)
        # Actual execution
        self.data_collector = locations.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.config['LOCATIONS'] = dict(LOCATIONS)
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_requests.called)
        self.assertTrue(mock_zipfile.called)
        self.assertTrue(mock_bytes.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertFalse(self.data_collector.config['LOCATIONS']['Kabul']['missing'])
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(1, self.data_collector.state['data_elements'])
        self.assertEqual(1, self.data_collector.state['inserted_elements'])
        self.assertEqual(self.data_collector.config['MAX_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])

    @mock.patch('data_gathering_subsystem.data_modules.locations.locations.BytesIO')
    @mock.patch('zipfile.ZipFile')
    @mock.patch('requests.get')
    @mock.patch('data_gathering_subsystem.data_modules.locations.locations.MongoDBCollection')
    def test_correct_data_collection_no_missing_locations_in_database(self, mock_collection, mock_requests,
                mock_zipfile, mock_bytes):
        # Mocking ZipFile
        mock_zipfile.return_value = Mock()
        mock_zipfile.return_value.open.return_value = BytesIO(DATA)
        mock_zipfile.return_value.infolist.return_value = [ZipInfo('cities1000.txt', (2018, 1, 2, 2, 13, 24))]
        # Mocking MongoDBCollection: initialization and operations
        mock_collection.return_value.find.return_value = ([{'name': 'Delhi'}, {'name': 'Mexico City'},
                {'name': 'Guatemala City'}, {'name': 'Cairo'}, {'name': 'Kabul'}], None)
        mock_collection.return_value.close.return_value = None
        mock_collection.return_value.collection.bulk_write.return_value = insert_result = Mock()
        insert_result.bulk_api_result = {'nInserted': 1, 'nMatched': 0, 'nUpserted': 0}
        # Actual execution
        self.data_collector = locations.instance(log_to_stdout=False, log_to_telegram=False)
        self.data_collector.config['LOCATIONS'] = dict(LOCATIONS)
        self.data_collector.run()
        self.assertTrue(mock_collection.called)
        self.assertTrue(mock_requests.called)
        self.assertTrue(mock_zipfile.called)
        self.assertTrue(mock_bytes.called)
        self.assertTrue(self.data_collector.finished_execution())
        self.assertTrue(self.data_collector.successful_execution())
        self.assertIsNotNone(self.data_collector.state['data_elements'])
        self.assertIsNotNone(self.data_collector.state['inserted_elements'])
        self.assertEqual(0, self.data_collector.state['data_elements'])
        self.assertEqual(0, self.data_collector.state['inserted_elements'])
        self.assertTrue(self.data_collector.advisedly_no_data_collected)
        self.assertEqual(self.data_collector.config['MAX_UPDATE_FREQUENCY'],
                         self.data_collector.state['update_frequency'])
