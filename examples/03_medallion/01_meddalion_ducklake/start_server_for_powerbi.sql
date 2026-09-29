-- Expose DuckLake as a Quack server to Power BI
-- cd C:\_cmps360-content\examples\03_medallion\01_meddalion_ducklake
-- Start the server using:
-- duckdb -init "start_server_for_powerbi.sql"
-- When connecting, enter the URI from your quack_serve call 
-- (e.g. quack:127.0.0.1:9494) as the server address. 
-- Set motherduck_tocken as localtoken 
-- When prompted for credentials, enter cmps360 as the Key
-- Use these steps to connect to the server from Power BI: 
-- https://github.com/CurtHagenlocher/quack-net#using-the-power-bi-connector

INSTALL ducklake;
LOAD ducklake;

ATTACH
'ducklake:C:/_cmps360-content/examples/03_medallion/01_meddalion_ducklake/lakehouse/sales_lake_catalog.db'
AS sales_lake;

INSTALL quack;
LOAD quack;

CALL quack_serve('quack:127.0.0.1:9494', token => 'cmps360');