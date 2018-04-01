

if (!exists("monitordir")) monitordir='.'
filename="updates.csv"
set terminal png size 3000,800
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


plot data using 1:4 with lines dashtype 4 lt rgb "violet" axes x1y1 \
          title "Parallel Downloads (Target)"  ,\
     data using 1:6 with lines dashtype 1 lt rgb "violet" axes x1y1 \
          title "Parallel Downloads"           ,\
     data using 1:5 with lines dashtype 4 lt rgb "cyan"   axes x1y2 \
          title "Sequential Downloads (Target)",\
     data using 1:7 with lines dashtype 1 lt rgb "cyan"   axes x1y2 \
          title "Sequential Downloads"

