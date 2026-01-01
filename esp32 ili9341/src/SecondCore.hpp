#pragma once

#include <Arduino.h>
#include <BluetoothSerial.h>
#include <stdint.h>
#include <freertos/FreeRTOS.h>

extern BluetoothSerial SerialBT;
extern QueueHandle_t btQueue;

struct SystemInformation {
  uint8_t CPU_Usage;
  uint8_t RAM_Usage;
  uint8_t GPU_Usage;
  uint8_t VRAM_Usage;
  uint8_t GPU_Temperature;
  uint32_t System_Time;
};

void btTask(void *pvParameters) {
  String incoming;
  while (true) {
    if (SerialBT.available()) {
      char c = SerialBT.read();
      incoming += c;

      if (incoming.endsWith("\r\n")) {
        SerialBT.write('A');
        
        int start = 0;
        int end = incoming.indexOf('\n');

        SystemInformation result = {0, 0, 0, 0, 0, 0};

        while (end != -1) {
          String line = incoming.substring(start, end);
          line.trim();

          int sep = line.indexOf('=');
          if (sep != -1) {
            String key = line.substring(0, sep);
            String value = line.substring(sep + 1);

            uint32_t integer_value = value.toInt();

            if (key.equals("CPU Usage")) {
              result.CPU_Usage = (uint8_t) integer_value;
            } else if (key.equals("GPU Usage")) {
              result.GPU_Usage = (uint8_t) integer_value;
            } else if (key.equals("RAM Usage")) {
              result.RAM_Usage = (uint8_t) integer_value;
            } else if (key.equals("VRAM Usage")) {
              result.VRAM_Usage = (uint8_t) integer_value;
            } else if (key.equals("GPU Temperature")) {
              result.GPU_Temperature = (uint8_t) integer_value;
            } else if (key.equals("System Time")) {
              result.System_Time = integer_value;
            }
          }

          start = end + 1;
          end = incoming.indexOf('\n', start);
        }

        if (xQueueSend(btQueue, &result, portMAX_DELAY) == pdPASS) {
          incoming = "";
        }
      }
    }
    vTaskDelay(10 / portTICK_PERIOD_MS);
  }
}


void start_second_core() {
  xTaskCreatePinnedToCore(
    btTask,
    "BT Task",
    4096,
    NULL,
    1,
    NULL,
    1
  );
}