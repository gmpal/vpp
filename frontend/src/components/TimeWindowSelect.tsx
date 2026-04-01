import React from "react";
import {
    FormControl,
    InputLabel,
    MenuItem,
    Select,
    SelectChangeEvent,
} from "@mui/material";
import { TIME_WINDOW_OPTIONS } from "../timeWindow";

interface TimeWindowSelectProps {
    value: number;
    onChange: (minutes: number) => void;
    label?: string;
}

const TimeWindowSelect: React.FC<TimeWindowSelectProps> = ({
    value,
    onChange,
    label = "Time window",
}) => {
    const handleChange = (event: SelectChangeEvent<string>) => {
        onChange(Number(event.target.value));
    };

    return (
        <FormControl size="small" sx={{ minWidth: 220 }}>
            <InputLabel id="time-window-label">{label}</InputLabel>
            <Select
                labelId="time-window-label"
                value={String(value)}
                label={label}
                onChange={handleChange}
            >
                {TIME_WINDOW_OPTIONS.map((option) => (
                    <MenuItem key={option.minutes} value={String(option.minutes)}>
                        {option.label}
                    </MenuItem>
                ))}
            </Select>
        </FormControl>
    );
};

export default TimeWindowSelect;