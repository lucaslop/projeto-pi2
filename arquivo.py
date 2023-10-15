import os
import time
import sys
import json
import random
import paho.mqtt.client as mqtt
from threading import Thread

# Thingsboard platform credentials
THINGSBOARD_HOST = 'demo.thingsboard.io'  # Change IP Address
ACCESS_TOKEN = 'hQho5Bpls94UH5Pwq4IA'

hora_inicio = time.time()

def calcular_nivel_bateria():
    # Dados do robô cortador de grama
    tensao_bateria = 18  # Volts
    capacidade_bateria = 2.5  # Ah
    tempo_corte_por_carga = 5  # minutos
    area_por_carga = 50  # m²

    # Calcula a energia total disponível na bateria (Wh)
    energia_bateria = tensao_bateria * capacidade_bateria

    # Calcula o consumo de energia por minuto (Wh/min)
    energia_por_minuto = energia_bateria / tempo_corte_por_carga

    # Calcula o nível de bateria restante com base no tempo de operação atual
    tempo_atual = time.time()
    tempo_decorrido_minutos = (tempo_atual - hora_inicio) / 60  # Tempo decorrido em minutos
    energia_restante = energia_bateria - (energia_por_minuto * tempo_decorrido_minutos)
    energia_restante = max(energia_restante, 0)

    # Calcula a porcentagem de bateria restante
    nivel_bateria = (energia_restante / energia_bateria) * 100

    return nivel_bateria

sensor_data = {
    'led_ligar': 'false',
    'led_iniciar_corte': 'false',
    'swligar': 'false',
    'sw_iniciar_corte': 'false',
    'bateria': calcular_nivel_bateria(),
    'led_erro': 'false'
}

def toggle_led_ligar():
    sensor_data['led_ligar'] = sensor_data['swligar']   

def toggle_led_iniciar_corte():
    if(sensor_data['led_ligar'] == True and sensor_data['led_erro'] != 'true'):
        sensor_data['led_iniciar_corte'] = sensor_data['sw_iniciar_corte']

def emulate_sensor_data():
    while True:
        # Emular a temperatura com pequenas variações (por exemplo, entre 24 e 26 graus Celsius)
        sensor_data['temperatura'] = random.uniform(24, 26)

        # Emular a umidade com pequenas variações (por exemplo, entre 40% e 60%)
        sensor_data['humidity'] = random.uniform(40, 60)

        time.sleep(5)  # Aguarda 5 segundos antes de atualizar novamente

# Function will set the temperature value in the device
def setValue(params):
    sensor_data['temperature'] = params
    print("Temperature Set:", params, "C")

def publishValue(client):
    INTERVAL = 2
    print("Thread Started")
    next_reading = time.time()
    area = 0.0
    t = Thread(target=emulate_sensor_data)
    t.start()
    while True:
        toggle_led_ligar()
        toggle_led_iniciar_corte()
        if sensor_data['led_iniciar_corte'] == True:
            sensor_data['bateria'] = calcular_nivel_bateria()
            area = max(100 - sensor_data['bateria'], 0)
        sensor_data['telemetry'] = {
            'temperatura': sensor_data['temperatura'],
            'humidity': sensor_data['humidity'],
            'led_ligar': sensor_data['led_ligar'],
            'led_iniciar_corte': sensor_data['led_iniciar_corte'],
            'bateria': sensor_data['bateria'],
            'area': area,
            'led_erro': sensor_data['led_erro']
        }
        client.publish('v1/devices/me/telemetry', json.dumps(sensor_data['telemetry']), 1)
        next_reading += INTERVAL
        sleep_time = next_reading - time.time()
        if sleep_time > 0:
            time.sleep(sleep_time)
# MQTT on_connect callback function
def on_connect(client, userdata, flags, rc):
    client.subscribe('v1/devices/me/rpc/request/+')



def ligarLedErro():
    if sensor_data['led_erro'] == 'false':
        sensor_data['led_erro'] = 'true'
    else:
        sensor_data['led_erro'] = 'false'


# MQTT on_message callback function
def on_message(client, userdata, msg):
    if msg.topic.startswith('v1/devices/me/rpc/request/'):
        requestId = msg.topic[len('v1/devices/me/rpc/request/'):]
        data = json.loads(msg.payload)
        if data['method'] == 'getValuePainel':
            client.publish('v1/devices/me/rpc/response/' + requestId, json.dumps(sensor_data['temperature']), 1)
        if data['method'] == 'setValuePainel':
            params = data['params']
            setValue(params)
            toggle_led_ligar()  # Update status after toggling the LED
        if data['method'] == 'getValueSWLigar':
            client.publish('v1/devices/me/rpc/response/' + requestId, json.dumps(sensor_data['swligar']), 1)

        if data['method'] == 'setValueSWLigar':
            new_swligar_state = data['params']
            sensor_data['swligar'] = new_swligar_state
            toggle_led_ligar()  # Update status after toggling the LED

        if data['method'] == 'getValueSWIniciarCorte':
            client.publish('v1/devices/me/rpc/response/' + requestId, json.dumps(sensor_data['sw_iniciar_corte']), 1)

        if data['method'] == 'setValueSWIniciarCorte':
            new_sw_iniciar_corte_state = data['params']
            sensor_data['sw_iniciar_corte'] = new_sw_iniciar_corte_state
            toggle_led_iniciar_corte()

        if data['method'] == 'simularerro':
            ligarLedErro()
            sensor_data['led_iniciar_corte'] = False
            


       

# create a client instance
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.username_pw_set(ACCESS_TOKEN)
client.connect(THINGSBOARD_HOST, 1883, 60)

t = Thread(target=publishValue, args=(client,))

try:
    client.loop_start()
    t.start()
    while True:
        pass

except KeyboardInterrupt:
    client.disconnect()
    exit(1)
