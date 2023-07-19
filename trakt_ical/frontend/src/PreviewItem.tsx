import { Pill } from "./Pill";
import type {
  MovieItem,
  MovieData,
  MoviesResponse,
  ShowItem,
  ShowData,
  ShowsResponse,
} from "./types/api_responses";
export interface IPreviewItemProps {
  type_of: "shows" | "movies";
  data: ShowItem | MovieItem | undefined;
}

export const PreviewItem = ({ ...props }: IPreviewItemProps): JSX.Element => {
  // air_time
  // if type === show use airs_at_unix else use released_unix

  const air_time =
    props.type_of === "shows"
      ? props.data?.airs_at_unix
      : props.data?.released_unix;

  // convert to 12 hour time using Date object
  var air_time_str = air_time
    ? new Date(air_time * 1000).toLocaleTimeString("en-US", {
        hour: "numeric",
        minute: "numeric",
        hour12: true,
      })
    : "Unknown";

  return (
    <div className="border-solid border-[#2a2a2a]/20 border-[0.5px] flex flex-col gap-0 items-center justify-end w-[350px] h-[200px] relative overflow-hidden">
      <div className="absolute top-0 left-0 w-[350px] h-[200px] bg-[#000000]/50 z-10"></div>

      <div className="absolute top-0 left-0 w-full h-full z-0">
        <img
          className="w-[350px] h-[200px] relative"
          src={props.data?.background ?? "https://via.placeholder.com/350x200"}
        />
      </div>
      <img
        className="shrink-0 w-[193.47px] h-[75px] relative z-10"
        src={props.data?.logo ?? "https://via.placeholder.com/193.47x75"}
      />

      <div className="pt-[15px] pr-2.5 pb-[15px] pl-2.5 flex flex-col gap-[5px] items-start justify-end self-stretch shrink-0 relative z-10">
        <div className="flex flex-col gap-[5px] items-start justify-end self-stretch shrink-0 relative">
          <div className="flex flex-row gap-[5px] items-end justify-start shrink-0 relative">
            <Pill type_of="time" text={air_time_str} />
            <Pill type_of="network" text="network" />
          </div>

          <div
            className="text-[#ffffff] text-left relative self-stretch whitespace-nowrap max-w-[290px] overflow-hidden overflow-ellipsis"
            style={{ font: "700 16px 'Inter', sans-serif" }}
          >
            {props.data?.title}
          </div>

          <div
            className="text-[#ffffff] text-left relative self-stretch"
            style={{ font: "400 12px 'Inter', sans-serif" }}
          >
            {props.type_of === "shows" ? (
              <>
                {props.data?.show} S
                {props.data?.season?.toString().padStart(2, "0")}E
                {props.data?.number?.toString().padStart(2, "0")}
              </>
            ) : (
              <>
                {props.data?.released_unix
                  ? new Date(props.data?.released_unix * 1000).getFullYear()
                  : "Unknown"}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
