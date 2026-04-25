set path=E:\PostgreSQL 17.2\bin
call raster2pgsql -s 4269 -I -C -M D:\桌面\实验3数据\092g06_e.dem\092g06_e.dem -F -t 56x56 public.dem092g06e | psql -d exp3 -U postgres -p 5432
pause