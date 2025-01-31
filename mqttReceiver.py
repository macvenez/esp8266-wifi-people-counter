from influxdb_client import InfluxDBClient, BucketRetentionRules
from influxdb_client.client.write_api import SYNCHRONOUS

import paho.mqtt.client as mqtt
import time
import datetime
import snifferconfig as cfg


def on_message(client, userdata, message):
    mac = str(message.payload.decode("utf-8"))
    if mac != "":
        if mac_randomizer_mode:
            mac_half = mac[0:6]
            last15mResults = influxclient.query(
                "SELECT activity FROM traffic_accounting WHERE mac =~ /^"
                + mac_half
                + "/ and time > now() - 15m;"
            )
        else:
            last15mResults = influxclient.query(
                "SELECT activity FROM traffic_accounting WHERE mac = '"
                + mac
                + "' and time > now() - 15m;"
            )
        last15mPoints = last15mResults.get_points()
        last15mPoints = list(last15mPoints)
        twoHoursResults = influxclient.query(
            "SELECT activity FROM traffic_accounting WHERE mac = '"
            + mac
            + "' and time > now() - 2h;"
        )
        twoHoursPoints = twoHoursResults.get_points()
        twoHoursPoints = list(twoHoursPoints)
        allResults = influxclient.query(
            "SELECT activity FROM traffic_accounting WHERE mac = '" + mac + "';"
        )
        allPoints = allResults.get_points()
        allPoints = list(allPoints)
        lenAllPoints = len(allPoints)
        if len(last15mPoints) == 0 and len(twoHoursPoints) > 6:
            json_insert = [
                {
                    "measurement": "traffic_accounting",
                    "tags": {"mac": mac, "permanent": "yes"},
                    "fields": {"activity": 1, "total_activity": lenAllPoints},
                }
            ]

            write_api.write(bucket=cfg.db_name, record=json_insert)

            if log:
                logfile.write("%s,PERMANENT,%s\r\n" % (mac, datetime.datetime.now()))
            if debug:
                print(
                    "MAC Received:",
                    mac,
                    "ADDED AS PERMANENT at",
                    datetime.datetime.now(),
                )
        elif len(last15mPoints) == 0 and len(twoHoursPoints) <= 6:
            json_insert = [
                {
                    "measurement": "traffic_accounting",
                    "tags": {"mac": mac, "permanent": "no"},
                    "fields": {"activity": 1, "total_activity": lenAllPoints},
                }
            ]
            write_api.write(bucket=cfg.db_name, record=json_insert)
            if log:
                logfile.write(
                    "%s,NOT PERMANENT,%s\r\n" % (mac, datetime.datetime.now())
                )
            if debug:
                print(
                    "MAC Received:",
                    mac,
                    "ADDED AS NOT PERMANENT at",
                    datetime.datetime.now(),
                )
        else:
            if log:
                logfile.write(
                    "%s,NOT ADDED (TOO SOON),%s\r\n" % (mac, datetime.datetime.now())
                )
            if debug:
                print(
                    "MAC Received:",
                    mac,
                    "NOT ADDED BECAUSE RECENT PREVIOUS PRESENCE DETECTED < 15M at",
                    datetime.datetime.now(),
                )


debug = True
log = True
mac_randomizer_mode = False  # to avoid WiFi mac randomizer mode

if log:
    logfile = open("log.csv", "a")


# Influx setup
# influxclient = InfluxDBClient(host=cfg.db_address, port=cfg.db_port)
# influxclient.switch_database(cfg.db_name)

with InfluxDBClient(
    url=cfg.db_address, token=cfg.db_token, org=cfg.db_org
) as influxclient:
    write_api = influxclient.write_api(write_options=SYNCHRONOUS)

"""buckets_api = influxclient.buckets_api()

	# Create Bucket with retention policy set to 0 seconds
	retention_rules = BucketRetentionRules(type="expire", every_seconds=0)
	created_bucket = buckets_api.create_bucket(
		bucket_name=cfg.db_name, retention_rules=retention_rules, org=cfg.db_org
	)
	"""


# print("creating new instance")
mqttclient = mqtt.Client("mqttsniffer")  # create new instance
mqttclient.username_pw_set(cfg.broker_user, cfg.broker_password)

# print("connecting to broker")
mqttclient.connect(cfg.broker_address, port=cfg.broker_port)  # connect to broker
mqttclient.loop_start()

# print("Subscribing to topic")
mqttclient.subscribe(cfg.broker_topic)
mqttclient.on_message = on_message  # attach function to callback

try:
    while True:
        time.sleep(1)

except KeyboardInterrupt:
    print("bye")
    if log:
        logfile.close()
    mqttclient.disconnect()
    mqttclient.loop_stop()
