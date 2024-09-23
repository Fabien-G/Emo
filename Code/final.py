import time
from board import SCL, SDA
import busio
from adafruit_servokit import ServoKit
import multiprocessing
import RPi.GPIO as GPIO
import os
import sys 
import logging
import spidev as SPI
from PIL import Image, ImageDraw, ImageFont
from random import randint

# Pins pour les capteurs tactiles et de vibration
touch_pin = 17
vibration_pin = 22

# Configuration des GPIO pour les capteurs
GPIO.setmode(GPIO.BCM)
GPIO.setup(touch_pin, GPIO.IN)
GPIO.setup(vibration_pin, GPIO.IN)

# Configuration des pins pour l'écran LCD sur le Raspberry Pi
RST = 27
DC = 25
BL = 18
bus = 0 
device = 0 

# Initialisation du kit de servos
kit = ServoKit(channels=16)

# Déclaration des servos sur des canaux spécifiques
servoR = kit.servo[5]  # Servo droit, référence à 0 degrés
servoL = kit.servo[11] # Servo gauche, référence à 180 degrés
servoB = kit.servo[13] # Servo central, référence à 90 degrés

# Dictionnaire pour stocker le nombre d'images pour chaque émotion
frame_count = {
    'blink': 39, 'happy': 60, 'sad': 47, 'dizzy': 67, 'excited': 24, 
    'neutral': 61, 'happy2': 20, 'angry': 20, 'happy3': 26, 'bootup3': 124, 
    'blink2': 20
}

# Liste d'émotions aléatoires à déclencher
emotion = ['angry', 'sad', 'excited']

# Liste d'états normaux/neutres
normal = ['neutral', 'blink2']

# Création d'une file d'attente pour les émotions et d'un événement pour la synchronisation des processus
q = multiprocessing.Queue()
event = multiprocessing.Event()

# Fonction pour vérifier les capteurs tactiles et de vibration
def check_sensor():
    previous_state = 1  # État précédent du capteur tactile
    current_state = 0   # État actuel
    while True:
        # Vérifier l'état du capteur tactile
        if GPIO.input(touch_pin) == GPIO.HIGH:
            if previous_state != current_state:
                if q.qsize() == 0:
                    event.set()  # Déclencher l'événement si la file d'attente est vide
                    q.put('happy')  # Ajouter l'émotion "happy" dans la file
                current_state = 1
            else:
                current_state = 0
        # Vérifier l'état du capteur de vibration
        if GPIO.input(vibration_pin) == 1:
            print('vib')
            if q.qsize() == 0:
                event.set()
                # Ajouter une émotion aléatoire dans la file
                q.put(emotion[randint(0, 2)])
        time.sleep(0.05)  # Délai pour limiter la vérification rapide

# Fonction pour positionner les servos dans une position neutre (90 degrés)
def servoMed():
    servoR.angle = 90
    servoL.angle = 90
    servoB.angle = 90

# Fonction pour abaisser les servos
def servoDown():
    servoR.angle = 0
    servoL.angle = 180
    servoB.angle = 90

# Fonction pour faire tourner le servo central avec des mouvements de va-et-vient
def baserotate(reference, change, timedelay):
    for i in range(reference, reference + change, 1):
        servoB.angle = i
        time.sleep(timedelay)
    for j in range(reference + change, reference - change, -1):
        servoB.angle = j
        time.sleep(timedelay)
    for k in range(reference - change, reference, 1):
        servoB.angle = k
        time.sleep(timedelay)

# Fonction pour lever les bras du robot de bas en haut
def HandDownToUp(start, end, timedelay):
    for i, j in zip(range(0 + start, end, 1), range((180 - start), (180 - end), -1)):
        servoR.angle = i
        servoL.angle = j
        time.sleep(timedelay)

# Fonction pour abaisser les bras du robot de haut en bas
def HandUpToDown(start, end, timedelay):
    for i, j in zip(range(0 + start, end, -1), range((180 - start), (180 - end), 1)):
        servoR.angle = i
        servoL.angle = j
        time.sleep(timedelay)

# Fonction pour contrôler la rotation des bras du robot
def rotate(start, end, timedelay):
    if start < end:
        HandDownToUp(start, end, timedelay)
        HandUpToDown(end, start, timedelay)
    else:
        HandUpToDown(end, start, timedelay)
        HandDownToUp(start, end, timedelay)

# Fonction pour simuler une animation de bonheur avec les servos
def happy():
    servoMed()
    for n in range(5):
        for i in range(0, 120):
            if i <= 30:
                servoR.angle = 90 + i
                servoL.angle = 90 - i
                servoB.angle = 90 - i
            if 30 < i <= 90:
                servoR.angle = 150 - i
                servoL.angle = i + 30
                servoB.angle = i + 30
            if i > 90:
                servoR.angle = i - 30
                servoL.angle = 210 - i
                servoB.angle = 210 - i
            time.sleep(0.004)

# Fonction pour simuler une animation de colère
def angry():
    for i in range(5):
        baserotate(90, randint(0, 30), 0.01)

# Autre animation de colère
def angry2():
    servoMed()
    for i in range(90):
        servoR.angle = 90 - i
        servoL.angle = i + 90
        servoB.angle = 90 - randint(-12, 12)
        time.sleep(0.02)

# Animation de tristesse
def sad():
    servoDown()
    for i in range(0, 60):
        if i <= 15:
            servoB.angle = 90 - i
        if 15 < i <= 45:
            servoB.angle = 60 + i
        if i > 45:
            servoB.angle = 150 - i
        time.sleep(0.09)

# Animation d'excitation
def excited():
    servoDown()
    for i in range(0, 120):
        if i <= 30:
            servoB.angle = 90 - i
        if 30 < i <= 90:
            servoB.angle = i + 30
        if i > 90:
            servoB.angle = 210 - i
        time.sleep(0.01)

# Animation de clignotement
def blink():
    servoR.angle = 0
    servoL.angle = 180
    servoB.angle = 90

# Séquence d'initialisation au démarrage
def bootup():
    show('bootup3', 1)
    for i in range(1):
        p2 = multiprocessing.Process(target=show, args=('blink2', 3))
        p3 = multiprocessing.Process(target=rotate, args=(0, 150, 0.005))
        p4 = multiprocessing.Process(target=baserotate, args=(90, 45, 0.01))
        p2.start()
        p3.start()
        p4.start()
        p4.join()
        p2.join()
        p3.join()

# Fonction pour jouer un son correspondant à une émotion
def sound(emotion):
    for i in range(1):
        os.system("aplay /home/pi/Desktop/EmoBot/sound/" + emotion + ".wav")

# Fonction pour afficher une séquence d'images correspondant à une émotion
def show(emotion, count):
    for i in range(count):
        try:
            disp = LCD_2inch.LCD_2inch()
            disp.Init()
            for i in range(frame_count[emotion]):
                image = Image.open('/home/pi/Desktop/EmoBot/emotions/' + emotion + '/frame' + str(i) + '.png')
                disp.ShowImage(image)
        except IOError as e:
            logging.info(e)
        except KeyboardInterrupt:
            disp.module_exit()
            servoDown()
            logging.info("quit:")
            exit()

# Fonction principale exécutée au lancement
if __name__ == '__main__':
    p1 = multiprocessing.Process(target=check_sensor, name='p1')
    p1.start()
    bootup()
    
    while True:
        if event.is_set():
            p5.terminate()
            event.clear()
            emotion = q.get()
            q.empty()
            print(emotion)
            p2 = multiprocessing.Process(target=show, args=(emotion, 4))
            p3 = multiprocessing.Process(target=sound, args=(emotion,))
            if emotion == 'happy':
                p4 = multiprocessing.Process(target=happy)
            elif emotion == 'angry':
                p4 = multiprocessing.Process(target=angry)
            elif emotion == 'sad':
                p4 = multiprocessing.Process(target=sad)
            elif emotion == 'excited':
                p4 = multiprocessing.Process(target=excited)
            elif emotion == 'blink':
                p4 = multiprocessing.Process(target=blink)
            else:
                continue
            p2.start()
            p3.start()
            p4.start()
            p2.join()
            p3.join()
            p4.join()
        else:
            p = multiprocessing.active_children()
            for i in p:
                if i.name not in ['p1', 'p5', 'p6']:
                    i.terminate()
            neutral = normal[0]
            p5 = multiprocessing.Process(target=show, args=(neutral, 4), name='p5')
            p6 = multiprocessing.Process(target=baserotate, args=(90, 60, 0.02), name='p6')
            p5.start()
            p6.start()
            p6.join()
            p5.join()
