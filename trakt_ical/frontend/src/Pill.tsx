export interface IPillProps {
  type_of?: "time" | "network";
  text: string;
}

export const Pill = ({ ...props }: IPillProps): JSX.Element => {
  const classStr = {
    time: "bg-[#ed1c24] rounded-sm pt-[3px] pr-1 pb-[3px] pl-1 flex flex-row gap-2.5 items-start justify-start shrink-0 relative",
    network:
      "bg-[#555555] rounded-sm pt-[3px] pr-1 pb-[3px] pl-1 flex flex-row gap-2.5 items-start justify-start shrink-0 relative",
  };

  return (
    <div className={classStr[props.type_of ?? "time"]}>
      <div
        className="text-[#ffffff] text-left relative"
        style={{ font: "600 11px 'Inter', sans-serif" }}
      >
        {props.text}
      </div>
    </div>
  );
};
