drop table sec_filer;
drop table sec_report;

create table if not exists sec_filer (
    name text not null primary key,
    cik text not null
);

create table if not exists sec_report (
    cik text not null,
    dirname text not null,
    name text,
    adsh text,
    period text,
    fy text,
    fp text,
    filed text,
    detail text,
    primary key (cik, dirname)
);
