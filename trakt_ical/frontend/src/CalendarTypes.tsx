import React from "react";

export interface ICalendarTypeActiveDefaultProps {
  active?: boolean;
  text: string;
  onClick?: () => void; // New prop for onClick event
}

export const CalendarType = ({
  active = false,
  text,
  onClick, // Destructure the onClick prop
}: ICalendarTypeActiveDefaultProps): JSX.Element => {
  const classStr = {
    default:
      "text-[#ed1c24] text-left relative hover:underline hover:cursor-pointer",
    inactive:
      "text-[#ffffff] text-left relative hover:underline hover:cursor-pointer",
  };

  return (
    <div
      className="flex flex-row gap-2.5 items-start justify-start shrink-0 w-full relative"
      onClick={onClick} // Pass onClick event to the div
    >
      <div
        className={active ? classStr["default"] : classStr["inactive"]}
        style={{ font: "700 32px 'Inter', sans-serif" }}
      >
        {text}
      </div>
    </div>
  );
};

export default CalendarType;
