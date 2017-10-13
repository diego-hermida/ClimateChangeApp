import threading


class DataCollector(threading.Thread):

    def __init__(self, data_module):
        self.data_module = data_module
        threading.Thread.__init__(self)

    def run(self):
        data = self.data_module.get_data()
        self.data_module.save_data(data)
