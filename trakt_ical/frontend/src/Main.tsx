import { CalendarTypeActiveDefault } from "./CalendarTypeActiveDefault";
import { DayPreviewStatusDefault } from "./DayPreviewStatusDefault";
import React from "react";
import type {
  MovieItem,
  MovieData,
  MoviesResponse,
  ShowItem,
  ShowData,
  ShowsResponse,
} from "./types/api_responses";
import { useCallback, useEffect, useRef, useState } from "react";

export interface IFrame1Props {}

export const Main = ({ ...props }: IFrame1Props): JSX.Element => {
  const key = new URLSearchParams(window.location.search).get("key");
  const base_url = window.location.href.split("?")[0];

  if (!key) {
    window.location.href = `${base_url}/auth`;
    return <div></div>;
  }

  const [calendarData, setCalendarData] = React.useState(
    null as ShowsResponse | MoviesResponse | null,
  );
  const [calendarType, setCalendarType] = React.useState<
    "shows" | "movies"
  >("shows");
  const [daysAgo, setDaysAgo] = React.useState(30);
  const [daysAhead, setDaysAhead] = React.useState(90);
  const [userinfo, setUserinfo] = React.useState({
    username: "",
    slug: "",
  });
  const [calendarUrl, setCalendarUrl] = React.useState<string>("");

  const debouncedFetch = useRef(
    debounce((url: string) => {
      fetch(url)
        .then((response) => response.json())
        .then((data) => {
          setCalendarData(data as ShowsResponse | MoviesResponse);
        });
    }, 500),
  ).current;

  React.useEffect(() => {
    debouncedFetch(calendarUrl);
  }, [calendarUrl]);

  function handleCalendarTypeChange(type: "shows" | "movies") {
    setCalendarType(type);
  }

  function addCalendarProtocol(
    protocol: "webcal" | "google" | "outlook365" | "outlooklive",
  ) {
    const webcal_url = `${base_url}${calendarType}?key=${key}&days_ago=${daysAgo}&period=${daysAhead}`.replace(
      "https://", "webcal://"
    ).replace(
      "http://", "webcal://"
    );

    let addCalendarUrl = "";

    switch (protocol) {
      case "webcal":
        addCalendarUrl = webcal_url;
        break;
      case "google":
        addCalendarUrl = `https://calendar.google.com/calendar/render?cid=${encodeURIComponent(
          webcal_url,
        )}`;
        break;
      case "outlook365":
        addCalendarUrl = `https://outlook.office.com/owa?path=%2Fcalendar%2Faction%2Fcompose&rru=addsubscription&url=${encodeURIComponent(
          webcal_url,
        )}&name=Trakt%20iCal`;
        break;
      case "outlooklive":
        addCalendarUrl = `https://outlook.live.com/owa?path=%2Fcalendar%2Faction%2Fcompose&rru=addsubscription&url=${encodeURIComponent(
          webcal_url,
        )}&name=Trakt%20iCal`;
        break;
    }

    return addCalendarUrl;
  }

  React.useEffect(() => {
    const url = `${base_url}${calendarType}/json?key=${key}&days_ago=${daysAgo}&period=${daysAhead}`;
    setCalendarUrl(url);
  }, [calendarType, daysAgo, daysAhead]);

  React.useEffect(() => {
    fetch(`${base_url}api/user/${key}`)
      .then((response) => response.json())
      .then((data) => {
        setUserinfo(data);
      });
  }, []);

  return (
    <div className="bg-[#1d1d1d] flex flex-col md:flex-row gap-0 items-start justify-start max-w-full relative overflow-hidden min-h-[100svh] md:max-h-screen select-text">
      <div className="border-solid border-[rgba(196,196,196,0.20)] md:border-r flex flex-col gap-2.5 items-start justify-start self-stretch shrink-0  w-full md:w-[350px] relative overflow-hidden">
        <div className="pt-5 pr-10 pb-2 pl-10 flex flex-col gap-2.5 items-start justify-center self-stretch shrink-0 relative overflow-hidden">
          <div
            className="text-[#ffffff] text-left relative self-stretch"
            style={{ font: "700 40px 'Inter', sans-serif" }}
          >
            Trakt Calendar
          </div>
        </div>

        <div className="pl-10 pr-10 flex flex-col gap-2.5 items-start justify-start self-stretch shrink-0 relative text-[#d4d4d4]/50 text-sm">
          <p>
            Showing <strong>{userinfo.username}'s</strong> calendar
          </p>
        </div>

        <div className="flex flex-col gap-2.5 items-start justify-start self-stretch flex-1 relative">
          <div className="flex flex-col gap-[5px] items-start justify-start self-stretch shrink-0 relative overflow-hidden">
            <div className="pt-[5px] pr-10 pb-[5px] pl-10 flex flex-row gap-2.5 items-start justify-start self-stretch shrink-0 relative">
              <div
                className="text-[#d4d4d4] text-left relative"
                style={{ font: "400 16px 'Inter', sans-serif" }}
              >
                Calendars
              </div>
            </div>
            <CalendarTypeActiveDefault
              active={calendarType === "shows" ? true : false}
              text="Shows"
              onClick={() => handleCalendarTypeChange("shows")}
            />
            <CalendarTypeActiveDefault
              text="Movies"
              onClick={() => handleCalendarTypeChange("movies")}
              active={calendarType === "movies" ? true : false}
            />
          </div>
          <div className="flex flex-col gap-[5px] items-start justify-start self-stretch shrink-0 relative overflow-hidden">
            <div className="pt-[5px] pr-10 pb-[5px] pl-10 flex flex-row gap-2.5 items-start justify-start self-stretch shrink-0 relative">
              <div
                className="text-[#d4d4d4] text-left relative"
                style={{ font: "400 16px 'Inter', sans-serif" }}
              >
                Time Frame
              </div>
            </div>

            <div className="pr-10 pl-10 flex flex-row gap-2.5 items-start justify-start self-stretch shrink-0 relative">
              <div
                className="text-[#d4d4d4] text-left relative flex flex-col gap-2.5"
                style={{ font: "700 24px 'Inter', sans-serif" }}
              >
                <label
                  htmlFor="days_ago"
                  className="text-[#d4d4d4] text-left relative font-normal text-xs"
                >
                  Days Ago
                </label>
                <input
                  type="number"
                  id="days_ago"
                  max={30}
                  min={1}
                  className="w-[100px] h-[40px] border-solid border-[rgba(196,196,196,0.20)] border-[1px] rounded-[5px] bg-[#1d1d1d] text-[#ffffff] text-left relative pl-[10px] pr-[10px] pt-[5px] pb-[5px] font-normal text-sm"
                  style={{ font: "400 16px 'Inter', sans-serif" }}
                  value={daysAgo}
                  onChange={(e) => setDaysAgo(parseInt(e.target.value))}
                />
              </div>
            </div>

            <div className="pr-10 pl-10 flex flex-row gap-2.5 items-start justify-start self-stretch shrink-0 relative">
              <div
                className="text-[#d4d4d4] text-left relative flex flex-col gap-2.5"
                style={{ font: "700 24px 'Inter', sans-serif" }}
              >
                <label
                  htmlFor="days_ahead"
                  className="text-[#d4d4d4] text-left relative font-normal text-sm"
                >
                  Days Ahead
                </label>
                <input
                  type="number"
                  id="days_ahead"
                  max={90}
                  min={1}
                  className="w-[100px] h-[40px] border-solid border-[rgba(196,196,196,0.20)] border-[1px] rounded-[5px] bg-[#1d1d1d] text-[#ffffff] text-left relative pl-[10px] pr-[10px] pt-[5px] pb-[5px] font-normal text-sm"
                  style={{ font: "400 16px 'Inter', sans-serif" }}
                  value={daysAhead}
                  onChange={(e) => setDaysAhead(parseInt(e.target.value))}
                />
              </div>
            </div>
          </div>
          <div className="pt-5 pb-5 flex flex-col gap-2.5 items-start justify-end self-stretch flex-1 relative overflow-hidden">
            <ClickableText
              text="Add to Google Calendar"
              target={addCalendarProtocol("google")}
            />
            <ClickableText
              text="Add to Outlook 365"
              target={addCalendarProtocol("outlook365")}
            />
            <ClickableText
              text="Add to Outlook"
              target={addCalendarProtocol("outlooklive")}
            />

            <div>
              <ClickableText
                text="Github"
                target="https://github.com/radityaharya/trakt_ical"
              />
            </div>
          </div>
          dsp
        </div>
      </div>

      <div
        className="flex flex-col gap-0 items-start justify-start self-stretch flex-1 relative"
        style={{ overflowY: "auto" }}
      >
        {calendarData?.data.map((item: ShowData | MovieData) => {
          return <DayPreviewStatusDefault data={item} type_of={calendarType} />;
        })}
      </div>
    </div>
  );
};

interface IClickableTextProps {
  text: string;
  target: string;
}

const ClickableText = ({ text, target }: IClickableTextProps) => {
  return (
    <div
      className={`pr-10 pl-10 flex flex-row gap-2.5 items-start justify-start self-stretch shrink-0 relative cursor-pointer`}
    >
      <div
        className={`text-[#ffffff] text-left relative`}
        style={{ font: "600 16px 'Inter', sans-serif" }}
        onClick={() => window.open(target, "_blank")}
      >
        {text}
      </div>
    </div>
  );
};

function debounce(func: Function, wait: number) {
  let timeout: ReturnType<typeof setTimeout>;

  return function (...args: any[]) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };

    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}
