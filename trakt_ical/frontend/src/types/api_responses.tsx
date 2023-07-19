interface MovieItem {
  overview: string;
  released: string;
  released_unix: number;
  runtime: number;
  title: string;
  background?: string;
  logo?: string;
  show?: string;
  season?: number;
  number?: number;
  airs_at_unix?: number;
}

interface MovieData {
  type: "movies";
  date_str: string;
  date_unix: number;
  items: MovieItem[];
}

interface MoviesResponse {
  data: MovieData[];
  type: "movies";
}

interface ShowItem {
  airs_at: string;
  airs_at_unix: number;
  number: number;
  overview: string | null;
  runtime: number | null;
  season: number;
  show: string;
  title: string;
  background?: string;
  logo?: string;
  released_unix?: number;
}

interface ShowData {
  type: "shows";
  date_str: string;
  date_unix: number;
  items: ShowItem[];
}

interface ShowsResponse {
  data: ShowData[];
  type: "shows";
}

export type {
  MovieItem,
  MovieData,
  MoviesResponse,
  ShowItem,
  ShowData,
  ShowsResponse,
};
