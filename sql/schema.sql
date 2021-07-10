create table if not exists sec_filer (
    name text primary key,
    cik text not null
);

create table if not exists sec_report (
    cik text,
    dirname text,
    name text,
    adsh text,
    period text not null,
    fy text not null,
    fp text not null,
    filed text not null,
    detail text not null,
    primary key (cik, dirname)
);
