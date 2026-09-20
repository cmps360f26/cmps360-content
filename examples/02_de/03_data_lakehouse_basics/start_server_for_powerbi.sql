-- Expose DuckLake as a Quack server to Power BI
-- Start the server using:
-- duckdb -init "start_server_for_powerbi.sql"
-- Use these steps to connect to the server from Power BI: 
-- https://github.com/CurtHagenlocher/quack-net#using-the-power-bi-connector

INSTALL ducklake;
LOAD ducklake;

ATTACH
'ducklake:C:/_cmps360-content/examples/02_de/03_data_lakehouse_basics/lakehouse/hr_lake_catalog.db'
AS hr_lake;

INSTALL quack;
LOAD quack;

CALL quack_serve('quack:127.0.0.1:9494', token => 'cmps360');