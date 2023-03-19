import PySimpleGUI as sg
import serial
import skyfield
from skyfield.api import N, W, wgs84, load
from skyfield import almanac
import time
from datetime import timedelta, timezone


class Target:

    def __init__(self,name):
        
        self.targetlist = [
            ('Moon','moon'),
            ('Sun','sun'),
            ('Venus','venus'),
            ('Jupiter','JUPITER BARYCENTER'),
            ('Mars','MARS BARYCENTER'),
            ('Saturn','SATURN BARYCENTER')
         ]
        
        self.target_dict = {key:value for key, value in self.targetlist}
        
        self.human_name = name
        self.target_name = self.target_dict[self.human_name]
        # Create a timescale and ask the current time.
        self.ts = load.timescale()
        self.is_above_horizon=False
        
        # Load the JPL ephemeris DE440s (covers 1849-2150).
        self.planets = load('de440s.bsp')
        self.earth = self.planets['earth']
        self.target = self.planets[self.target_name]
        
        # 52.388211 N, 2.304344 W, 69m above sea level
        self.wgs = wgs84.latlon(52.388211 * N, 2.304344 * W, 69)
        self.home = self.earth + self.wgs
 
        
        
    def run(self,window):
        while True:
            time.sleep(1)
            window.write_event_value(('-TARGET-', self.observe()), 'Done!')  
        
    def observe(self):   
        t = self.ts.now()
        astrometric = self.home.at(t).observe(self.target)
        alt, az, d = astrometric.apparent().altaz()
        if alt.degrees > 0.0:
            self.is_above_horizon =True
        else:
            self.is_above_horizon=False 
        
        return alt.degrees, az.degrees, d, t.astimezone(timezone(timedelta(0)))

    def set_target(self,name):
        self.human_name = name
        self.target_name = self.target_dict[self.human_name]
        try:
            self.target = self.planets[self.target_name]
        except Exception as e:
            print("Failed target name")
            print(e)
        
    def get_planets(self):
        return self.planets
    
    def get_rise_set(self):
        t0 = self.ts.now()
        t1 = t0 + timedelta(hours=24)
        f = almanac.risings_and_settings(self.planets, self.target, self.wgs)
        t, y = almanac.find_discrete(t0, t1, f)
        return zip(t, y)  

class Device:
    def __init__(self,baud):
        self.baud=baud
        self.running = False

    def set_port(self,port):
        self.portId=port


    def run(self,window):
        
        window['-COMMSTATUS-'].update('Connecting')
        try:
            self.ser = serial.Serial(
                port=self.portId,\
                baudrate=self.baud,\
                parity=serial.PARITY_NONE,\
                stopbits=serial.STOPBITS_ONE,\
                bytesize=serial.EIGHTBITS,\
                timeout=5)
        
            #this will store the line
            line = []
        
            self.running = True
            window['Disconnect'].update(disabled=False)
            window['-COMMSTATUS-'].update('Connected')
        
            while  self.running:
                for c in self.ser.read():
                    line.append(chr(c))
                    if c == 10:
                        window.write_event_value(('-THREAD-', ''.join(line)), 'Done!')
                        line = []
                        break
            
            self.ser.close()
            window['Connect'].update(disabled=False)
            window['Disconnect'].update(disabled=True)
            window['-COMMSTATUS-'].update('Disconnected')
        except:
            window['Connect'].update(disabled=False)
            window['Disconnect'].update(disabled=True)
            window['-COMMSTATUS-'].update('Unable to open')
    
    def is_running(self):    
        return self.running
    
    def is_stopped(self):    
        return not self.running
                
    def stop(self):
        self.running = False
        if hasattr(self,'ser'):
            while self.ser.is_open:
                time.sleep(1)
                
    def send(self,msg):
        if hasattr(self,'ser') and self.ser.is_open:
            self.ser.write(msg.encode())
        
    def __del__(self):
        self.running = False
        self.ser.close()
        
def get_cal_popup():
    cal_pop =[ 
              [sg.Text('Target Position: ', size=15, font = ("Arial", 14), justification='right'),
               sg.Text('', size=7, key='-TAR_AZ-',border_width=1,font = ("Arial", 14),justification='right'),
               sg.Text('', size=7, key='-TAR_EL-',border_width=1,font = ("Arial", 14),justification='right'),
              ],
              [sg.Text('Dish Position: ',size=15, font = ("Arial", 14), justification='right'),
               sg.Text('', size=7, key='-CUR_AZ-',border_width=1, font = ("Arial", 14),justification='right'),
               sg.Text('', size=7, key='-CUR_EL-',border_width=1,font = ("Arial", 14),justification='right'),],
            ]
    return cal_pop

def the_gui():

    sg.theme('Light Brown 3')
    
    menu_def = [['Settings', ['Home Position', 'Limits','Comms' ]], ['About']]
    
    angles =[ 
              [sg.Text('Target Position: ', size=15, font = ("Arial", 14), justification='right'),
               sg.Text('', size=7, key='-TAR_AZ-',border_width=1,font = ("Arial", 14),justification='right'),
               sg.Text('', size=7, key='-TAR_EL-',border_width=1,font = ("Arial", 14),justification='right'),
              ],
              [sg.Text('Dish Position: ',size=15, font = ("Arial", 14), justification='right'),
               sg.Text('', size=7, key='-CUR_AZ-',border_width=1, font = ("Arial", 14),justification='right'),
               sg.Text('', size=7, key='-CUR_EL-',border_width=1,font = ("Arial", 14),justification='right'),],
            ]
    status =[
              [sg.Text('Comms: ', size=10, font = ("Arial", 10), justification='right'),
               sg.Text('Disconnected', size=12, key='-COMMSTATUS-',font = ("Arial", 10),justification='left'),
              ],
              [sg.Text('Controller: ', size=10, font = ("Arial", 10), justification='right'),
               sg.Text('----', size=12, key='-STATUS-',font = ("Arial", 10),justification='left')
              ]
        ]
    times =[
              [sg.Text('Target: ', size=6, font = ("Arial", 10), justification='right'),
               sg.Combo(list(target.target_dict.keys()), key='-TARGETNAME-', default_value='Moon', enable_events=True)
              ],
              [sg.Text('Rise:', size=6, font = ("Arial", 10), justification='right'),
               sg.Text('---', size=16, key='-RISE-',font = ("Arial", 10),justification='left'),
              ],
              [sg.Text('Set:', size=6, font = ("Arial", 10), justification='right'),
               sg.Text('---', size=16, key='-SET-',font = ("Arial", 10),justification='left')
              ],
              [sg.Text('UTC:', size=6, font = ("Arial", 10), justification='right'),
               sg.Text('---', size=16, key='-UTC-',font = ("Arial", 10),justification='left')
              ]
        ]

    layout = [[sg.Menu(menu_def)],
              [
                 [ sg.Frame("Status",status,vertical_alignment='top', expand_y=True, expand_x=True),
                  sg.Frame("Times",times,vertical_alignment='bottom', expand_x=True), 
                 ]
              ],
              [sg.Frame("Target",angles),sg.Frame("Controls",[[
                    sg.Button('Track',disabled=True),
                    sg.Button('Align',disabled=True),
                    sg.Button('Stop',disabled=True)
                  ]],vertical_alignment='top', expand_y=True, expand_x=True)
              ],
              [sg.Text('Next ...',key='-VERBOSE-')],
              [sg.Output(size=(70, 10))],
              [sg.Text('Port'),
                  sg.Input(default_text='COM9', key='-PORT-', size=(6, 1)),
                  sg.Button('Connect', bind_return_key=True),
                  sg.Button('Disconnect', disabled=True),
              ]
            ]

    window = sg.Window('Moon Tracker', layout)
    window.finalize()
    window.start_thread(lambda: target.run(window), ('-TARGET-', '-TARGET ENDED-'))
    update_rise_set(window)

    # --------------------- EVENT LOOP ---------------------
    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, 'Exit'):
            break
        elif event == 'Connect':
            portId = values['-PORT-']
            print('Connecting to port {}'.format(portId))
            if conn.is_running():
                print("Already connected")
            else:
                conn.stop()
                conn.set_port(portId)
                window.start_thread(lambda: conn.run(window), ('-THREAD-', '-THREAD ENDED-'))
                window['Connect'].update(disabled=True)
        elif event == 'Disconnect':
            window['Connect'].update(disabled=True)
            window['Track'].update(disabled=True)
            window['Stop'].update(disabled=True)
            window['Align'].update(disabled=True)
            conn.stop()
            window['-STATUS-'].update('----')
        elif event == 'Track':
            conn.send('R\n')
        elif event == 'Stop':
            conn.send('S\n')
        elif event == 'Align':
            conn.send('Z\n')
            #sg.popup(sg.Frame("foo",get_cal_popup()))
        elif event == 'Moon':
            update_target(window,target.observe())
        elif event[0] == '-THREAD-':
            #print('Data: ', event[1])
            processData(window,event[1])
        elif event[0] == '-TARGET-':
            update_target(window,event[1])
        elif event == '-TARGETNAME-':
            if conn.is_running():
                conn.send('S\n')
            #window['-TARGETOBJ-'].update(values['-TARGETNAME-'])
            target.set_target(values['-TARGETNAME-'])
            update_rise_set(window)
    # if user exits the window, then close the window and exit the GUI func
    window.close()


def update_rise_set(window):
        window['-RISE-'].update('---')
        window['-SET-'].update('---')
        for ti, yi in target.get_rise_set():
            if yi:
                window['-RISE-'].update(ti.utc_iso())
            else:
                window['-SET-'].update(ti.utc_iso())


def update_target(window,data):
    window['-TAR_EL-'].update('{0:.2f}'.format(data[0]))
    window['-TAR_AZ-'].update('{0:.2f}'.format(data[1]))
    rise=''
    sets=''
    for ti, yi in target.get_rise_set():
        if yi:
            rise = ti - target.ts.now()
            rise = divmod(rise*24*60,60)
        else:
            sets=ti - target.ts.now()
            sets = divmod(sets*24*60,60)
    try:
        if target.is_above_horizon:
            window['-VERBOSE-'].update(target.human_name+' is above the horizon and sets in '+str(int(sets[0]))+' hours and '+str(int(sets[1]))+' minutes')
        else:
            window['-VERBOSE-'].update(target.human_name+' is below the horizon and rises in '+str(int(rise[0]))+ ' hours and '+str(int(sets[1]))+' minutes')
    except Exception as e:
        print("Failed above/below")
        print(e)
    window['-UTC-'].update(data[3])
    if conn.is_running():
        conn.send('E{0:.2f}\n'.format(data[0]));
        conn.send('A{0:.2f}\n'.format(data[1]));

def processData(window,data):
    foo = data.split(',')

    if foo[0]=="POS":
        window['-CUR_EL-'].update('{0:.2f}'.format(float(foo[2])))
        window['-CUR_AZ-'].update('{0:.2f}'.format(float(foo[1])))

        
    elif foo[0]=='STATUS':
        stat = foo[1].rstrip()
        if stat =='RUN':
            window['Stop'].update(disabled=False)
            window['Align'].update(disabled=True)
            window['Track'].update(disabled=True)
            window['-STATUS-'].update('Tracking')
        elif stat =='STOP':
            window['Stop'].update(disabled=True)
            window['Align'].update(disabled=False)
            window['Track'].update(disabled=False)
            window['-STATUS-'].update('Stopped')
    
    
if __name__ == '__main__':
    conn = Device(115200)
    target = Target('Moon') 
    the_gui()
    print('Exiting Program')

