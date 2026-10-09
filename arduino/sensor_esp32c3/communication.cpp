// ============================================================
// ESP-NOW COMMUNICATION - SENSOR ESP32-C3
// ============================================================
//
// This file handles wireless communication between the moving
// ESP32-C3 sensor node and the stationary base ESP32.
//
// Main jobs:
//
// - Start ESP-NOW
// - Register the base ESP32 as a peer
// - Receive the "MEASURE" command
// - Read the sensors
// - Send the measurement back to the base ESP32
//
// The receive callback only records that a command arrived.
// The actual sensor reading happens later in
// processWirelessCommunication().
// ============================================================


#include "communication.h"
#include "config.h"
#include "sensors.h"

#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>

#include <math.h>
#include <string.h>


// ============================================================
// COMMUNICATION STATE
// ============================================================

// Becomes true once ESP-NOW has started successfully.

static bool communicationReady = false;


// Set to true when a MEASURE command arrives.
//
// The callback only changes this flag.
// The actual measurement is done later in loop().

static volatile bool measurementRequested = false;


// ============================================================
// CHECK MAC ADDRESS
// ============================================================
//
// Returns false while BASE_ESP32_MAC is still:
// 00:00:00:00:00:00

static bool baseMacConfigured()
{
    for (int i = 0; i < 6; i++)
    {
        if (BASE_ESP32_MAC[i] != 0)
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
// This function is automatically called by ESP-NOW whenever
// a wireless message arrives.
//
// Keep this callback short.
// We only identify the command and set a flag.

static void onDataReceived(
    const esp_now_recv_info_t *info,
    const uint8_t *data,
    int dataLength
)
{
    // Ignore invalid packets.

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
    //
    // Only accept commands from the known base ESP32.

    if (
        memcmp(
            info->src_addr,
            BASE_ESP32_MAC,
            6
        ) != 0
    )
    {
        return;
    }


    // --------------------------------------------------------
    // COPY RECEIVED MESSAGE
    // --------------------------------------------------------

    char message[64];

    int copyLength =
        dataLength;

    if (
        copyLength
        >= sizeof(message)
    )
    {
        copyLength =
            sizeof(message) - 1;
    }


    memcpy(
        message,
        data,
        copyLength
    );

    message[copyLength] = '\0';


    // --------------------------------------------------------
    // INTERPRET COMMAND
    // --------------------------------------------------------

    if (
        strcmp(
            message,
            "MEASURE"
        ) == 0
    )
    {
        measurementRequested = true;
    }
}


// ============================================================
// INITIALIZE ESP-NOW
// ============================================================

bool beginWirelessCommunication()
{
    communicationReady = false;


    // --------------------------------------------------------
    // CHECK BASE MAC ADDRESS
    // --------------------------------------------------------

    if (!baseMacConfigured())
    {
        Serial.println(
            "ERR,Base ESP32 MAC address not configured"
        );

        return false;
    }


    // --------------------------------------------------------
    // WI-FI STATION MODE
    // --------------------------------------------------------

    WiFi.mode(
        WIFI_STA
    );


    // Both ESP32 devices must use the same Wi-Fi channel.

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
    // REGISTER BASE ESP32 AS PEER
    // --------------------------------------------------------

    esp_now_peer_info_t peerInfo = {};

    memcpy(
        peerInfo.peer_addr,
        BASE_ESP32_MAC,
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
            "ERR,Failed to add base ESP32 as ESP-NOW peer"
        );

        return false;
    }


    communicationReady = true;


    Serial.println(
        "ESP-NOW sensor communication ready"
    );


    return true;
}


// ============================================================
// SEND WIRELESS MESSAGE
// ============================================================

bool sendWirelessMessage(
    const char* message
)
{
    if (
        !communicationReady
        || message == nullptr
    )
    {
        return false;
    }


    esp_err_t result =
        esp_now_send(
            BASE_ESP32_MAC,
            (const uint8_t*)message,
            strlen(message) + 1
        );


    return (
        result == ESP_OK
    );
}


// ============================================================
// PROCESS WIRELESS COMMANDS
// ============================================================
//
// This function is called repeatedly from loop().
//
// If a MEASURE request has arrived:
//
// 1. Read sensors
// 2. Check the data
// 3. Create a response message
// 4. Send it back to the base ESP32

void processWirelessCommunication()
{
    if (!measurementRequested)
    {
        return;
    }


    // Clear the request before taking the measurement.

    measurementRequested = false;


    // --------------------------------------------------------
    // READ SENSORS
    // --------------------------------------------------------

    float speed;
    float pressure;
    float temperature;


    readAll(
        speed,
        pressure,
        temperature
    );


    // --------------------------------------------------------
    // CHECK MEASUREMENTS
    // --------------------------------------------------------

    if (
        isnan(speed)
        || isnan(pressure)
        || isnan(temperature)
    )
    {
        sendWirelessMessage(
            "ERR,Sensor measurement not available"
        );

        return;
    }


    // --------------------------------------------------------
    // BUILD RESPONSE
    // --------------------------------------------------------

    char response[128];


    snprintf(
        response,
        sizeof(response),
        "OK,MEASURE,%.6f,%.6f,%.6f",
        speed,
        pressure,
        temperature
    );


    // --------------------------------------------------------
    // SEND TO BASE ESP32
    // --------------------------------------------------------

    sendWirelessMessage(
        response
    );
}


// ============================================================
// COMMUNICATION STATUS
// ============================================================

bool wirelessCommunicationReady()
{
    return communicationReady;
}