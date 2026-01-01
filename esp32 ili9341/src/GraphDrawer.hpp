#pragma once

#include <Arduino.h>
#include <TFT_eSPI.h>
#include <stdint.h>

class GraphInformation {
public:
    GraphInformation(uint8_t _size, uint8_t _sbp) : size(_size), space_between_points(_sbp), dp(0) {
        data = new uint8_t[_size];
    }

    ~GraphInformation() {
        delete[] data;
    }

    /**
     * @brief Pushes the data into the "push-back" buffer `uint8_t* data`
     */
    void push(uint8_t b) {
        if (dp < size) {
            data[dp] = b;            
            dp++;
        } else {
            // Since we are not controlling a very big buffer like 100 or 200, remember max size is 255 anyways so no matter.
            // This O(n) functioning will be fine.
            // In the final design, I am using 15 bytes big buffer -_-
            for (uint8_t i = 0; i < size - 1; i++) {
                data[i] = data[i + 1];
            }
            data[size - 1] = b;
        }
    }

    /**
     * @brief Draws the ring-buffer data to the sprite
     * @param map_min_value, map_max_value used in the map() function to map the data to a range
     */
    void drawGraph(TFT_eSprite& sprite, uint16_t map_min_value, uint16_t map_max_value, uint16_t color) {
        sprite.drawFastHLine(0, 119, 160, TFT_WHITE);
        sprite.drawFastVLine(0, 0, 120, TFT_WHITE);

        uint16_t x = 0;
        int16_t prevX = -1;
        int16_t prevY = -1;

        for (uint8_t i = 0; i < dp; i++) {
            uint8_t b = data[i];
            uint16_t mapped = map(b, 0, 255, map_max_value, map_min_value);

            sprite.drawPixel(x, mapped, color);

            if (prevX > 0) {
                sprite.drawLine(prevX, prevY, x, mapped, color);
            }

            prevX = x;
            prevY = mapped;            
            x += space_between_points;
        }
    }
private:
    uint8_t* data;
    uint8_t size;
    uint8_t dp;
    uint8_t space_between_points;
};