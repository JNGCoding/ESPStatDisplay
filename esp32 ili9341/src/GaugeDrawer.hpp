#pragma once

#include <stdint.h>
#include <TFT_eSPI.h>
#include "Free_Fonts.h"

class GaugeInformation {
public:
    GaugeInformation(uint8_t start_progress, String text) : progress(start_progress), name(text) {}
    GaugeInformation() : progress(0), name("") {}

    void increment() {
        progress++;
    }

    void decrement() {
        progress--;
    }

    void setProgress(uint8_t new_progress) {
        progress = new_progress;
    }

    uint8_t getProgress() {
        return progress;
    }

    void setName(String text) {
        name = text;
    }

    String& getName() {
        return name;
    }

    void fillArc(TFT_eSprite& Sprite, int32_t x, int32_t y, int32_t r, int32_t ir, uint32_t startAngle, uint32_t endAngle, uint32_t fg_color, uint32_t bg_color, bool smoothArc = true, uint32_t n = 1) {
        for (int i = 0; i < n; i++) {
            Sprite.drawArc(x, y, r - i, ir, startAngle, endAngle, fg_color, bg_color, smoothArc);
        }
    }

    void drawGauge(TFT_eSprite& sprite) {
        uint32_t end_angle = map(progress, 0, 100, 45, 315);

        uint32_t totalSpan = 315 - 45;
        uint32_t segSpan   = totalSpan / 3;

        uint32_t seg1Start = 45;
        uint32_t seg1End   = 45 + segSpan - 5;

        uint32_t seg2Start = seg1End + 5;
        uint32_t seg2End   = seg2Start + segSpan - 5;

        uint32_t seg3Start = seg2End + 5;
        uint32_t seg3End   = 315;

        if (end_angle > seg1Start) {
            uint32_t seg_end = min(end_angle, seg1End);
            fillArc(sprite, 50, 50, 49, 50, seg1Start, seg_end, TFT_GREEN, TFT_BLACK, true, 10);
        }

        if (end_angle > seg2Start) {
            uint32_t seg_end = min(end_angle, seg2End);
            fillArc(sprite, 50, 50, 49, 50, seg2Start, seg_end, TFT_YELLOW, TFT_BLACK, true, 10);
        }

        if (end_angle > seg3Start) {
            uint32_t seg_end = min(end_angle, seg3End);
            fillArc(sprite, 50, 50, 49, 50, seg3Start, seg_end, TFT_RED, TFT_BLACK, true, 10);
        }

        String s = String(progress);

        sprite.setFreeFont(FM12);
        sprite.setCursor((100 - sprite.textWidth(s)) / 2, 55);
        sprite.printf(s.c_str());

        sprite.setFreeFont(NULL);
        sprite.drawString("%", (100 - sprite.textWidth("%")) / 2, 65);

        sprite.setFreeFont(FMB12);
        sprite.setCursor((100 - sprite.textWidth(name)) / 2, 100);
        sprite.print(name.c_str());
    }
private:
    uint8_t progress;
    String name;    
};