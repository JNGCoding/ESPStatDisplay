#include <Arduino.h>
#include <TFT_eSPI.h>
#include <WiFi.h>
#include <math.h>
#include <freertos/FreeRTOS.h>
#include "Free_Fonts.h"
#include "GaugeDrawer.hpp"
#include "GraphDrawer.hpp"
#include "SecondCore.hpp"

//////////////////////////////////////////////////////////////////////////////////////////////
//^ VARIABLES
TFT_eSPI Display = TFT_eSPI();
TFT_eSprite DialSprite = TFT_eSprite(&Display);
TFT_eSprite GraphSprite = TFT_eSprite(&Display);
TFT_eSprite TimeSprite = TFT_eSprite(&Display);

GaugeInformation CPU(0, "CPU");
GaugeInformation GPU(0, "GPU");
GaugeInformation RAM(0, "RAM");

GraphInformation GPU_Usage_Data(15, 10);
GraphInformation CPU_Usage_Data(15, 10);
GraphInformation RAM_Usage_Data(15, 10);

uint8_t page = 0;

BluetoothSerial SerialBT;
QueueHandle_t btQueue;
SystemInformation currentState;
String SystemTime_Decoded = "";
//////////////////////////////////////////////////////////////////////////////////////////////

//////////////////////////////////////////////////////////////////////////////////////////////
//* FUNCTIONS

/**
 * @brief This function halts the xtensa processor of ESP32
 */
void halt() __attribute__((__noreturn__));
void halt() {
  while (true) { delay(1000); yield(); }
}

/**
 * @brief draws the GPU Temperature text onto the screen at the hardcoded coordinates
 * @param temp the temperature which will be drawn
 */
void drawGpuTemp(uint8_t temp) {
  Display.setFreeFont(FMB18);
  Display.fillRect(0, 190, 0 + Display.textWidth("100 *C"), 230, TFT_BLACK);
  Display.setCursor(0, 230);
  uint8_t mapped_temperature = map(temp, 0, 100, 0, 255);
  Display.setTextColor( Display.color565(mapped_temperature, 128 - (mapped_temperature / 2), 255 - mapped_temperature) );
  Display.printf("%u *C", temp);
}

/**
 * @brief just prints the system information received from the Computer.
 * @param information SystemInformation struct reference which stores all the data.
 */
void printState(SystemInformation& information) {
  Serial.println("---- System Information ----");
  Serial.printf("CPU Usage: %u%%\n", information.CPU_Usage);
  Serial.printf("RAM Usage: %u%%\n", information.RAM_Usage);
  Serial.printf("GPU Usage: %u%%\n", information.GPU_Usage);
  Serial.printf("VRAM Usage: %u%%\n", information.VRAM_Usage);
  Serial.printf("GPU Temperature: %u°C\n", information.GPU_Temperature);
  Serial.printf("System Time (packed): %lu\n", information.System_Time);
  Serial.println("----------------------------");
}

/**
 * @brief Draws all the static graphics which do not change with time after being drawn. Specially for the System information screen.
 */
void drawDefaultStatPage() {
  Display.setRotation(1);
  Display.setCursor(0, 0);
  Display.fillScreen(TFT_BLACK);

  Display.setFreeFont(NULL);
  Display.setTextColor(TFT_GREENYELLOW);
  Display.setCursor(320 / 2 - 20, 240 / 2 + 7);
  Display.print("CPU");

  Display.setTextColor(TFT_ORANGE);
  Display.setCursor(320 / 2 - 20, 240 / 2 + 14 + 4);
  Display.print("GPU");

  Display.setTextColor(TFT_CYAN);
  Display.setCursor(320 / 2 - 20, 240 / 2 + 21 + 8);
  Display.print("RAM");

  Display.setTextColor(TFT_WHITE);
  Display.setFreeFont(FMB24);
  Display.setCursor(0, 160);
  Display.print("GPU");
  Display.setCursor(0, 190);
  Display.print("TEMP");

  DialSprite.fillSprite(TFT_BLACK);

  CPU.setProgress(0);
  CPU.drawGauge(DialSprite);
  DialSprite.pushSprite(0, 0);

  DialSprite.fillSprite(TFT_BLACK);

  GPU.setProgress(0);
  GPU.drawGauge(DialSprite);
  DialSprite.pushSprite(110, 0);

  DialSprite.fillSprite(TFT_BLACK);

  RAM.setProgress(0);
  RAM.drawGauge(DialSprite);
  DialSprite.pushSprite(220, 0);

  drawGpuTemp(0);

  GraphSprite.fillSprite(TFT_BLACK);

  CPU_Usage_Data.drawGraph(GraphSprite, 0, 120, TFT_GREENYELLOW);  
  GPU_Usage_Data.drawGraph(GraphSprite, 0, 120, TFT_ORANGE);
  RAM_Usage_Data.drawGraph(GraphSprite, 0, 120, TFT_CYAN);
  
  GraphSprite.pushSprite(320 / 2, 240 / 2);
}

/**
 * @brief This is a basic function which draws a simple text (time str) on to the Sprite buffer.
 */
void drawTime(String timeStr, TFT_eSprite& spr) {
  spr.fillSprite(TFT_BLACK);

  spr.setFreeFont(FMB24);
  int16_t w = spr.textWidth(timeStr);
  int16_t h = spr.fontHeight();

  int16_t x = (spr.width() - w) / 2;
  int16_t y = (spr.height() + h) / 2;

  spr.setTextColor(TFT_DARKGREY);
  spr.setCursor(x + 2, y + 2);
  spr.print(timeStr);

  spr.setTextColor(TFT_WHITE);
  spr.setCursor(x, y);
  spr.print(timeStr);

  static bool pulse = false;
  uint16_t color = pulse ? TFT_CYAN : TFT_MAGENTA;
  spr.drawLine(x, y + 6, x + w, y + 6, color);
  pulse = !pulse;
}
//////////////////////////////////////////////////////////////////////////////////////////////

void setup() {
  Serial.begin(115200);
  delay(10);

  SerialBT.begin("Statistics Display");
  Serial.println("Bluetooth started. Send strings ending with \\r\\n");

  SystemTime_Decoded.reserve(8);
  btQueue = xQueueCreate(10, sizeof(SystemInformation));  
  start_second_core();

  srand(esp_random() ^ micros());

  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(19, INPUT);

  Display.init();
  DialSprite.createSprite(100, 120);
  GraphSprite.createSprite(160, 120);

  Display.setFreeFont(FMB24);
  int16_t maxW = Display.textWidth("00:00:00");
  int16_t maxH = Display.fontHeight();

  TimeSprite.createSprite(maxW + 8, maxH + 28);

  drawDefaultStatPage();
}

uint32_t frame_time = 0;
void loop() {
  frame_time = millis();
  
  if (xQueueReceive(btQueue, &currentState, 0) == pdPASS) {
    printState(currentState);

    uint8_t hour = currentState.System_Time / 3600;
    uint8_t minute = (currentState.System_Time % 3600) / 60;
    uint8_t second = currentState.System_Time % 60;

    SystemTime_Decoded.clear();

    SystemTime_Decoded.concat(hour);
    SystemTime_Decoded.concat(":");
    SystemTime_Decoded.concat(minute);
    SystemTime_Decoded.concat(":");
    SystemTime_Decoded.concat(second);

    CPU_Usage_Data.push(currentState.CPU_Usage);
    GPU_Usage_Data.push(currentState.GPU_Usage);
    RAM_Usage_Data.push(currentState.RAM_Usage);
  }

  if (digitalRead(19)) {
    page = 1 - page;
    while (digitalRead(19)) yield();

    Display.fillScreen(TFT_BLACK);

    if (page == 0) {
      drawDefaultStatPage();
    } else {
    }
  }

  if (page == 0) {
    DialSprite.fillSprite(TFT_BLACK);

    CPU.setProgress(currentState.CPU_Usage);
    CPU.drawGauge(DialSprite);
    DialSprite.pushSprite(0, 0);

    DialSprite.fillSprite(TFT_BLACK);

    GPU.setProgress(currentState.GPU_Usage);
    GPU.drawGauge(DialSprite);
    DialSprite.pushSprite(110, 0);

    DialSprite.fillSprite(TFT_BLACK);

    RAM.setProgress(currentState.RAM_Usage);
    RAM.drawGauge(DialSprite);
    DialSprite.pushSprite(220, 0);

    drawGpuTemp(currentState.GPU_Temperature);

    GraphSprite.fillSprite(TFT_BLACK);

    CPU_Usage_Data.drawGraph(GraphSprite, 0, GraphSprite.height() - 1, TFT_GREENYELLOW);  
    GPU_Usage_Data.drawGraph(GraphSprite, 0, GraphSprite.height() - 1, TFT_ORANGE);
    RAM_Usage_Data.drawGraph(GraphSprite, 0, GraphSprite.height() - 1, TFT_CYAN);
    
    GraphSprite.pushSprite(320 / 2, 240 / 2);
  } else {
    drawTime(SystemTime_Decoded, TimeSprite);

    int16_t screenX = (320 - TimeSprite.width()) / 2;
    int16_t screenY = (240 - TimeSprite.height()) / 2;

    TimeSprite.pushSprite(screenX, screenY);
  }

  while (millis() - frame_time < 70) yield();
}
