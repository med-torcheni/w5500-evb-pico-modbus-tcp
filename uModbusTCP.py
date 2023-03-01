# Basic Modbus TCP Library
# Author : M.T
# Year : 2022

import usocket as socket
from uselect import select
from machine import Pin
import binascii, _thread

READ_HOLDING_REGISTERS = 0x03
WRITE_MULTIPLE_REGISTERS = 0x10

class ModbusTcpServer:
    def __init__(self, _host, _port, _non_blocking=False, _slave_id=1):
        self.host, self.port = _host, _port
        self.dataBank = [0] * 500
        self.slaveId = _slave_id
        self.nonBlocking = _non_blocking
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.inputs = [self.socket]
        self._start_server()

    def _start_server(self):
        self.socket.bind((self.host, self.port))
        self.socket.listen(8)
        if self.nonBlocking:
            th = _thread.start_new_thread(self._polling_thread, ())
    
    def _polling_thread(self):
        led = Pin(25, Pin.OUT)
        while True:
            led.toggle()
            try:
                self._send_receive(0)
            except Exception as e:
                print(e)
    
    def _send_receive(self, r):
        self.infds, self.outfds, self.errfds = select(self.inputs, [], [], 1/100000000)
        if self.infds:
            for fds in self.infds:
                if fds is self.socket:
                    if len(self.inputs) > 1:
                        self.inputs.remove(self.clientsock)
                    self.clientsock, self.clientaddr = fds.accept()
                    self.inputs.append(self.clientsock)
                else:
                    fp = fds.recv(6)
                    if not fp:
                        self.inputs.remove(self.clientsock)
                    else:
                        sp = fds.recv((fp[4] << 8) + fp[5])
                        if sp[0] == self.slaveId:
                            fds.send(self._client_handler(fds, fp, sp))
                        else:
                            pass

    def _wait_for_con(self):
        try:
            (self.clientsock, self.clientaddr) = self.socket.accept()
            print(f'{self.adress} is connected.')
        except:
            print('No one connected')
            
    def _read_tram(self):
        try:
            self.clientsock.recv(6)
            sp = fds.recv((fp[4] << 8) + fp[5])
            self.clientsock.send(self._client_handler(fds, fp, sp))
        except Exception as e:
            self.clientsock.close()
            self._wait_for_con()

    def _client_handler(self, client, fp, sp):
        fct = sp[1]
        try:
            if fct is READ_HOLDING_REGISTERS:
                adr, qty = (sp[2] << 8) + sp[3], (sp[4] << 8) + sp[5]
                if (qty > 125) or (adr + qty >= len(self.dataBank)):
                    return self.illegalData(fp)
                else:
                    return self.readHoldingRegisters(fp, sp, adr, qty)
            elif fct is WRITE_MULTIPLE_REGISTERS:
                adr, qty = (sp[2] << 8) + sp[3], (sp[4] << 8) + sp[5]
                btf = sp[6]
                if (qty > 125) or (adr + qty >= len(self.dataBank)):
                    return self.illegalData(fp)
                else:
                    return self.writeMultipleRegisters(fp, sp, adr, qty, btf)
            else:
                return self.illegalData(fp)
        except:
            pass

    def illegalData(self, fp):
        r = b''
        for i in range(2):
            if fp[i] <= 15:
                    r += chr(fp[i]).encode()
            else:
                r += binascii.unhexlify('%x' % fp[i])
        r += chr(0).encode() + chr(0).encode() + chr(0).encode() + chr(3).encode() + chr(3).encode() + binascii.unhexlify('%x' % 134) + chr(2).encode()
        return r


    def writeMultipleRegisters(self, fp, sp, adr, qty, btf):
        table = [0] * qty
        r = b''
        
        if self.slaveId <= 15:
            sp = chr(self.slaveId).encode() + sp[1:]
        else:
            sp =  binascii.unhexlify('%x' % self.slaveId) + sp[1:]
        
        for i in range(len(fp) - 1):
            if fp[i] <= 15:
                r += chr(fp[i]).encode()
            else:
                r += binascii.unhexlify('%x' % fp[i])
        r += chr(6).encode()
        for i in range(6):
            if sp[i] <= 15:
                r += chr(sp[i]).encode()
            else:
                r += binascii.unhexlify('%x' % sp[i])
        
        for i in range(qty):
            table[i] = (sp[7 + 2 * i] << 8) + sp[8 + 2 * i]
            
        for i in range(qty):
            self.dataBank[adr + i] = table[i]
        return r

    def readHoldingRegisters(self, fp, sp, adr, qty):
        responseLen = 9 + qty * 2
        TAB = [0] * responseLen
        for i in range(4):
            TAB[i] = fp[i]
        TAB[4] = ((qty * 2 + 3) & 0xff00) >> 8
        TAB[5] = (qty * 2 + 3) & 0xff
        TAB[6] = self.slaveId
        TAB[7] = sp[1]
        TAB[8] = qty * 2
        for i in range(qty):
            TAB[9 + 2 * i] = (self.dataBank[adr + i] & 0xff00) >> 8
            TAB[10 + 2 * i] = (self.dataBank[adr + i] & 0x00ff)

        r = b''
        for i in range(len(TAB)):
            if TAB[i] <= 15:
                r += chr(TAB[i]).encode()
            else:
                r += binascii.unhexlify('%x' % TAB[i])
        return r


