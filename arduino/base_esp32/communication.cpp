// ============================================================
// ESP-NOW COMMUNICATION - BASE ESP32
// ============================================================
//
// The base ESP32 sends measurement requests to the moving
// ESP32-C3 and receives the sensor results.
//
// Communication:
//
// Base ESP32
//     │
//     │ "MEASURE"
//     ▼
// Sensor ESP32-C3
//     │
//     │ "OK,MEASURE,speed,pressure,temperature"
//     ▼
// Base ESP32
// ============================================================


#include "communication.h"
#include "config.h"

#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>

#include <string.h>


// ============================================================
// COMMUNICATION STATE
// ============================================================

static bool communicationReady = false;


// Becomes true when a response from the sensor ESP32-C3
// has been received.

static volatile bool responseReceived = false;


// Stores the most recent wireless response.

static char receivedMessage[128];


// ============================================================
// CHECK MAC ADDRESS
// ============================================================

static bool sensorMacConfigured()
{
    for (int i = 0; i < 6; i++)
    {
        if (
            SENSOR_ESP32C3_MAC[i] != 0
        )
        {
            return true;
        }
    }

    return false;
}


// ============================================================
// RECEIVE CALLBACK
// ============================================================
//
// Automatically called when an ESP-NOW packet arrives.
//
// Keep this function short:
// copy the received message and set a flag.

static void onDataReceived(
    const esp_now_recv_info_t *info,
    const uint8_t *data,
    int dataLength
)
{
    if (
        info == nullptr
        || data == nullptr
        || dataLength <= 0
    )
    {
        return;
    }


    // --------------------------------------------------------
    // VERIFY SENDER
    // --------------------------------------------------------

    if (
        memcmp(
            info->src_addr,
            SENSOR_ESP32C3_MAC,
            6
        ) != 0
    )
    {
        return;
    }


    // --------------------------------------------------------
    // COPY MESSAGE
    // --------------------------------------------------------

    int copyLength =
        dataLength;


    if (
        copyLength
        >= sizeof(receivedMessage)
    )
    {
        copyLength =
            sizeof(receivedMessage) - 1;
    }


    memcpy(
        receivedMessage,
        data,
        copyLength
    );


    receivedMessage[copyLength] =
        '\0';


    // Tell the main program that a response is ready.

    responseReceived = true;
}


// ============================================================
// INITIALIZE ESP-NOW
// ============================================================

bool beginWirelessCommunication()
{
    communicationReady = false;


    // --------------------------------------------------------
    // CHECK MAC ADDRESS
    // --------------------------------------------------------

    if (!sensorMacConfigured())
    {
        Serial.println(
            "ERR,Sensor ESP32-C3 MAC address not configured"
        );

        return false;
    }


    // --------------------------------------------------------
    // WI-FI STATION MODE
    // --------------------------------------------------------

    WiFi.mode(
        WIFI_STA
    );


    // Both boards must use the same ESP-NOW channel.

    esp_err_t channelResult =
        esp_wifi_set_channel(
            ESPNOW_WIFI_CHANNEL,
            WIFI_SECOND_CHAN_NONE
        );


    if (
        channelResult != ESP_OK
    )
    {
        Serial.println(
            "ERR,Failed to set ESP-NOW channel"
        );

        return false;
    }


    // --------------------------------------------------------
    // START ESP-NOW
    // --------------------------------------------------------

    if (
        esp_now_init()
        != ESP_OK
    )
    {
        Serial.println(
            "ERR,ESP-NOW initialization failed"
        );

        return false;
    }


    // --------------------------------------------------------
    // REGISTER RECEIVE CALLBACK
    // --------------------------------------------------------

    if (
        esp_now_register_recv_cb(
            onDataReceived
        )
        != ESP_OK
    )
    {
        Serial.println(
            "ERR,Failed to register ESP-NOW receive callback"
        );

        return false;
    }


    // --------------------------------------------------------
    // REGISTER SENSOR ESP32-C3 AS PEER
    // --------------------------------------------------------

    esp_now_peer_info_t peerInfo = {};


    memcpy(
        peerInfo.peer_addr,
        SENSOR_ESP32C3_MAC,
        6
    );


    peerInfo.channel =
        ESPNOW_WIFI_CHANNEL;


    peerInfo.encrypt =
        false;


    peerInfo.ifidx =
        WIFI_IF_STA;


    if (
        esp_now_add_peer(
            &peerInfo
        )
        != ESP_OK
    )
    {
        Serial.println(
            "ERR,Failed to add sensor ESP32-C3 peer"
        );

        return false;
    }


    communicationReady = true;


    Serial.println(
        "ESP-NOW base communication ready"
    );


    return true;
}


// ============================================================
// REQUEST SENSOR MEASUREMENT
// ============================================================

bool requestSensorMeasurement(
    float &speed,
    float &pressure,
    float &temperature
)
{
    if (!communicationReady)
    {
        return false;
    }


    // Clear any old response.

    responseReceived = false;

    receivedMessage[0] =
        '\0';


    // --------------------------------------------------------
    // SEND MEASURE COMMAND
    // --------------------------------------------------------

    const char *command =
        "MEASURE";


    esp_err_t sendResult =
        esp_now_send(
            SENSOR_ESP32C3_MAC,
            (const uint8_t*)command,
            strlen(command) + 1
        );


    if (
        sendResult != ESP_OK
    )
    {
        return false;
    }


    // --------------------------------------------------------
    // WAIT FOR RESPONSE
    // --------------------------------------------------------

    unsigned long startTime =
        millis();


    while (!responseReceived)
    {
        if (
            millis() - startTime
            > SENSOR_RESPONSE_TIMEOUT_MS
        )
        {
            return false;
        }


        delay(1);
    }


    // --------------------------------------------------------
    // CHECK RESPONSE FORMAT
    // --------------------------------------------------------
    //
    // Expected:
    //
    // OK,MEASURE,12.4,84.2,22.7

    if (
        strncmp(
            receivedMessage,
            "OK,MEASURE,",
            11
        ) != 0
    )
    {
        return false;
    }


    // --------------------------------------------------------
    // EXTRACT SENSOR VALUES
    // --------------------------------------------------------

    int valuesRead =
        sscanf(
            receivedMessage,
            "OK,MEASURE,%f,%f,%f",
            &speed,
            &pressure,
            &temperature
        );


    if (
        valuesRead != 3
    )
    {
        return false;
    }


    return true;
}


// ============================================================
// COMMUNICATION STATUS
// ============================================================

bool wirelessCommunicationReady()
{
    return communicationReady;
}