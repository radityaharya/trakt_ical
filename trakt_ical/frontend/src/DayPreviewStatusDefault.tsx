import { PreviewItem } from "./PreviewItem";
import type {
  MovieItem,
  MovieData,
  MoviesResponse,
  ShowItem,
  ShowData,
  ShowsResponse,
} from "./types/api_responses";
export interface IDayPreviewStatusDefaultProps {
  status_of?: "default" | "no-content";
  type_of?: "shows" | "movies";
  data: ShowData | MovieData;
  error?: string | null;
}

const ItemPreviews = ({
  ...props
}: IDayPreviewStatusDefaultProps): JSX.Element => {
  return (
    <div className="scroll-container overflow-x-auto max-w-full">
      <div className="flex flex-row gap-0 items-start justify-start self-stretch w-[min-content]  relative">
        {props.data.items.map((item, index) => (
          <PreviewItem
            key={index}
            type_of={props.type_of as "shows" | "movies"}
            data={item as ShowItem | MovieItem}
          ></PreviewItem>
        ))}
      </div>
    </div>
  );
};

export const DayPreviewStatusDefault = ({
  ...props
}: IDayPreviewStatusDefaultProps): JSX.Element => {
  const isToday =
    new Date(props.data.date_unix * 1000).toDateString() ===
    new Date().toDateString();
  const dateColorString = isToday ? "#ed1c24" : "#ffffff";

  return (
    <div className="flex flex-col gap-0 items-start justify-start self-stretch shrink-0 relative overflow-hidden">
      <div className="bg-[#2a2a2a] pt-5 pr-6 pb-5 pl-6 flex flex-row gap-2.5 items-center justify-start self-stretch shrink-0 relative overflow-hidden">
        <div className="flex flex-row gap-[7px] items-center justify-start shrink-0 relative">
          <div
            className={`text-[${dateColorString}] text-left relative`}
            style={{ font: "700 36px 'Inter', sans-serif" }}
          >
            {new Date(props.data.date_unix * 1000).getDate()}
          </div>

          <div className="flex flex-col items-start justify-center shrink-0 relative">
            <div
              className={`text-[${dateColorString}] text-left relative`}
              style={{ font: "700 15px 'Inter', sans-serif" }}
            >
              {new Date(props.data.date_unix * 1000).toLocaleString("default", {
                month: "long",
              })}
            </div>

            <div
              className={`text-[${dateColorString}] text-left relative`}
              style={{
                margin: "-2px 0 0 0",
                font: "400 15px 'Inter', sans-serif",
              }}
            >
              {new Date(props.data.date_unix * 1000).toLocaleString("default", {
                weekday: "long",
              })}
            </div>
          </div>
        </div>
      </div>
      <ItemPreviews {...props} />
    </div>
  );
};
