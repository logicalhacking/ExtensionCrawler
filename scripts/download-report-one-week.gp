if (!exists("monitordir")) monitordir='.'
filename="updates.csv"
set terminal pngcairo size 3000,800 enhanced font 'Verdana,10'

set output monitordir."/download-report-one-week.png"

day="2018-04-01"
# basic configuration
set datafile separator ";"

set autoscale x

# plot last 7 days
set xrange [time(0) - 7*24*60*60:]

set ytics
set yrange [0:200000]
set ylabel "Parallel Downloads"
set ytics 25000
set mytics 2
set y2range [0:4000]
set y2label "Sequential Downloads"
set y2tics 500


set grid

set xdata time
set timefmt '%Y-%m-%d %H:%M:%S'
set format x "%Y-%m-%d\n%H:%M:%S"

set xtics 28800
set mxtics 8

set style data lines
set title sprintf("Extension Downloads (Last Seven Days)")

set key horiz
set key out bot center

# for plotting only one day, one can use:
data_for_day(day,file)=sprintf("<(grep %s %s)",day, file) 
data=data_for_day(day, monitordir."/".filename)

# for plotting all data
data=monitordir."/".filename

# Trick for plotting first derivative of data:
# x0=NaN
# y0=NaN
# replot data using (dx=$1-x0,x0=$1,$1-dx/2):(dy=$6-y0,y0=$6,dy/dx) w l notitle
# TODO: support time on x scale

x0p=NaN
y0p=NaN
x0s=NaN
y0s=NaN

plot data using 1:4 with lines dashtype 2 lt rgb "#d07b95" axes x1y1 \
          title "Parallel Downloads (Target)"  ,\
     data using 1:6 with lines lw 2 dashtype 1 lt rgb "#9c416e" axes x1y1 \
          title "Parallel Downloads"           ,\
     data using (dx=timecolumn(1)-x0p,x0p=timecolumn(1),timecolumn(1)-dx/2):(dy=$6-y0p,y0p=$6,dy/dx < 0 ? 0 : (8*60*60)*dy/dx) \
          with lines dashtype 2 lt rgb "#622a55" axes x1y1 \
          title "Parallel Downloads per Eight Hours",\
     data using 1:5 with lines dashtype 2 lt rgb "#76eec6" axes x1y2 \
          title "Sequential Downloads (Target)",\
     data using 1:7 with lines lw 2 dashtype 1 lt rgb "#5ebe9e" axes x1y2 \
          title "Sequential Downloads",\
     data using (dx=timecolumn(1)-x0s,x0s=timecolumn(1),timecolumn(1)-dx/2):(dy=$7-y0s,y0s=$7,dy/dx < 0 ? 0 : (8*60*60)*dy/dx) \
          with lines dashtype 2 lt rgb "#468e76" axes x1y2 \
          title "Sequential Downloads per Eight Hours"

set terminal pdfcairo size 30,8 enhanced font 'Verdana,15'
set output monitordir."/download-report-one-week.pdf"
replot
