from core import import_utils
from core.communication.ConvertTable import ConvertTable
from threading import RLock
import datetime
from PyQt5.Qt import QThread, pyqtSignal
from PyQt5.QtCore import QObject, pyqtSlot
from config import config
from inspect import isfunction
from communication.communication_utils import complitable_functions, get_converted_arguments

CoreModel = import_utils.import_class("modules/network_scan/%s.py" %
config["scanner"])
Parser = import_utils.import_class("modules/address_generation/%s.py" %
    config["parser"]
    )
IpGenerator = import_utils.import_class(
"modules/address_generation/%s.py" %
config["address_generator"]
)
JSONStorage = import_utils.import_class("modules/storage/%s.py" %
config["storage"])
convert_table = ConvertTable()
for func in import_utils.import_matching(
    "modules/convert_functions/",
    lambda name, value:
        isfunction(value) and value.__annotations__ 
):
    convert_table.add_function(func)
previous = IpGenerator.get_next_address
for function in [
    CoreModel.scan_address,
    JSONStorage.put_responce
    ]:
    msg = "%s is complitable with %s"
    if not complitable_functions(previous, function, convert_table):
        msg = "%s is not complitable with %s"
    print(msg % (function, previous))
    previous = function

class MainPresenter:
    def __init__(self, ui):
        self.ui = ui
        self.threads = []
        self.isScanEnabled = False
        self.parser = Parser()
        #needed config to specify path
        self.storage = JSONStorage("results.json")
        self.exit_lock = RLock()

    def startScan(self, ipRanges, portsStr, threadNumber, timeout):
        timeout = 3 if not timeout else int(timeout)
        addresses = None
        parser_args = {'port_field':portsStr, 'address_field':ipRanges}
        fields = self.parser.parse_fields(
                *get_converted_arguments(
                    self.parser.parse_fields,
                    parser_args,
                    convert_table
                )
            )
        self.scanner = CoreModel(timeout)
        if CoreModel.INDEPENDENT_THREAD_MANAGEMENT:
            addresses = self.parser.get_all_addresses(ipRanges)
            self.ip_generator = PlugAddressGenerator(addresses, ports)
            threadNumber = 1
        else:
            self.ip_generator = IpGenerator()
            self.ip_generator.set_parsed_fields(
                *get_converted_arguments(
                    self.ip_generator.set_parsed_fields,
                    fields,
                    convert_table
                    )
            )
            threadNumber = int(threadNumber)
            print("thread %i number set" % threadNumber)
        for i in range(threadNumber):
            print(i)
            scan_worker = ScanWorker(
                self.ip_generator,
                self.scanner,
                self.storage
                )
            scan_thread = QThread()
            scan_worker.log_signal.connect(self.log_text)
            scan_worker.moveToThread(scan_thread)
            scan_worker.exit_signal.connect(scan_thread.exit)
            scan_worker.exit_signal.connect(self.on_worker_exit)
            scan_thread.started.connect(scan_worker.work)
            self.threads.append((scan_worker, scan_thread))
        for thread in self.threads:
            scan_worker, scan_thread = thread
            print("starting")
            scan_thread.start()
        self.changeThreadLabel(threadNumber)

    def changeThreadLabel(self, number_of_threads):
        self.number_of_threads = number_of_threads
        self.ui.currentThreadsLabel.setText(str(number_of_threads))

    def on_worker_exit(self):
        self.changeThreadLabel(self.number_of_threads - 1)
        with self.exit_lock:
            for num, thread in enumerate(self.threads):
                    scan_worker, scan_thread = thread
                    if not scan_worker.isRunning:
                        self.threads.pop(num)
                        break
        if self.number_of_threads == 0:
            self.on_end_scanning()

    def on_end_scanning(self):
            self.isScanEnabled = False
            self.ui.startButton.setText("Start")
            self.storage.save()

    def stopScan(self):
        while self.threads:
            scan_worker, scan_thread = self.threads[0]
            if scan_worker.isRunning:
                scan_worker.stop()

    def log_text(self, string):
        self.ui.dataText.append("[" + str(datetime.datetime.now()) + "] " + str(string))


class ScanWorker(QObject):

    log_signal = pyqtSignal(str)
    exit_signal = pyqtSignal()

    def __init__(self, ip_generator, scanner, storage, **kwargs):
        super().__init__()
        self.ip_generator = ip_generator
        self.storage = storage
        self.scanner = scanner
        self.previous_address = None
        self.isRunning = True

    @pyqtSlot()
    def work(self):
        while self.isRunning:
            print("worker start")
            scan_address = self.ip_generator.get_next_address(
                *get_converted_arguments(
                    self.ip_generator.get_next_address,
                    self.previous_address,
                    convert_table
                )
            )
            if not scan_address:
                break
            scan_result = self.scanner.scan_address(
                    *get_converted_arguments(
                        self.scanner.scan_address,
                        scan_address,
                        convert_table
                    )
                )
            print(scan_result)
            scan_address.update(scan_result)
            self.previous_address = scan_address
            self.storage.put_responce(
                *get_converted_arguments(
                self.storage.put_responce,
                scan_address,
                convert_table
                    )
                )
            string_scan_address = " ".join(key + ":" + str(scan_address[key]) for
            key in scan_address.keys()) 
            if scan_result == 0:
                self.log_signal.emit('%s is open' % string_scan_address)
            else:
                self.log_signal.emit('%s is closed' % string_scan_address)
        self.stop()

    def stop(self):
        self.isRunning = False
        self.exit_signal.emit()
