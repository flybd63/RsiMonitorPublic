#!/usr/bin/perl
use strict;
use warnings;

use JSON;
use Time::Piece;
use DateTime;
use POSIX qw(strftime);

my $threshold = 90;
my $today = localtime->strftime('%Y%m%d');

my $mode = $ARGV[0];#P,S,G(プライム、スタンダード、グロース)
if( ! defined $mode || $mode eq ''){ $mode = "P"; };#指定なければプライムだけ

# メインルーチン
my %tikers = %{&load_mst()};
my $len = scalar(keys %tikers);
my $count = 0;
my %result = %{&load_result($today)};

foreach my $t (sort keys %tikers){
    $count++;

    #if($t ne "1941"){ next; }

    if( $mode =~ "P" && $tikers{$t}{class} =~ /^プライム/ ){}
    elsif( $mode =~ "S" && $tikers{$t}{class} =~ /^スタンダード/){}
    elsif( $mode =~ "G" && $tikers{$t}{class} =~ /^グロース/ ){}
    else{ next; }

    print STDERR "$count/$len t:$t $tikers{$t}{name} $tikers{$t}{class}\n";
    my $symbol = "$t.T";
    
    my ($last_end_date, @prices) = get_stock_data($symbol);

    if($#prices < 74){
        print STDERR "  - prices is short. skip. len: $#prices\n";
        next;
    }

    if (grep { !defined($_) } @prices) {
        print STDERR "princes has null. skip\n";
        next;
    }

    my $rsi = calculate_rsi(\@prices);
            
    $result{$t} = ();
    $result{$t}{rsi} = $rsi;
    $result{$t}{price} = $prices[-1];
    $result{$t}{end_date} = strftime("%Y-%m-%dT%H:%M:%S", gmtime($last_end_date));

    last;
}

my $now = DateTime->now(time_zone => 'GMT');
my $formatted_date = $now->strftime('%Y-%m-%dT%H:%M:%S');

my %out = (
    date_modified => $formatted_date,
    result => \%result
    );

print encode_json(\%out);

#&save_json($today, encode_json(\%result));
#&save_json("latest", encode_json(\%result));


#My %result = ($prices[0] => $prices[1]);

#open my $fh, '>', $output_file or die "Could not open file '$output_file': $!";
#print $fh encode_json(\%result);
#close $fh;
#print encode_json(\%result);

exit 0;


################################################################################
### SubRoutines ################################################################
################################################################################

sub load_mst {
    my $tikers_file = "./tickers.json";
    
    open(IN, $tikers_file);
    my $mst_jtxt = <IN>;
    close IN;
    my $mst_json = from_json($mst_jtxt);
    
    return $mst_json;
}

sub load_result {
    my ($date) = @_;
    my $result_file = "./result/$date.json";

    my $json = {};
    $json->{result} = {};
    
    if(-e $result_file){
        open(IN, $result_file);
        my $jtxt = <IN>;
        close IN;
        $json = from_json($jtxt);
    }        
    return $json->{result};
}

sub save_json {
    my ($ticker, $json) = @_;

    my $out = "./result/$ticker.json";
    my $tmpfile = $out."tmp";

    open( OUT, "> $tmpfile" ) or die $!;
    print OUT $json;
    close OUT;
    rename($tmpfile, $out);
    
}

# 株価データの取得
sub get_stock_data {
    my ($symbol) = @_;

    my $end_date = '0';
    my @prices = ();

    eval{
        my $url = '"https://query2.finance.yahoo.com/v8/finance/chart/'.$symbol.'?range=6mo&interval=1d"';
        
        #my $url = "https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=$symbol&apikey=$api_key";
        #my $response = $ua->get($url);
        my $response = `curl -sS $url`;

        #die "Failed to get data: ", $response->status_line unless $response->is_success;

        #my $data = decode_json($response->decoded_content);
        #print STDERR "ret:$response";
        my $data = decode_json($response);
        #my @prices = reverse( @{$data->{chart}{result}[0]{indicators}{quote}[0]{close}} );
        #splice(@prices, 76);

        @prices = @{$data->{chart}{result}[0]{indicators}{quote}[0]{close}};

        $end_date = $data->{chart}{result}[0]{meta}{currentTradingPeriod}{regular}{end};
        
        #    foreach my $date (sort keys %$time_series) {
        #        push @prices, $time_series->{$date}->{'4. close'};
        #    }
    };
    if($@){
        print STDERR "ERROR:symbol: $symbol\n$@";
    }
    return ($end_date, @prices);
}

# RSIを計算する関数
sub calculate_rsi {
    my $prices = shift;
    my $n = scalar(@$prices);
    
    my ($gain_sum, $loss_sum) = (0, 0);


    for (my $i = $n-14; $i < $n; $i++) {#直近の14日間だけみる

        my $diff = $prices->[$i] - $prices->[$i - 1];
        if ($diff > 0) {
            $gain_sum += $diff;
        } else {
            $loss_sum += abs($diff);
        }
    }

    my $rsi = 100 - (100 / (1 + ($gain_sum / $loss_sum)));
    return $rsi;
}

