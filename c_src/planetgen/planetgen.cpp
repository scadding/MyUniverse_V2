
#ifdef THINK_C
#define macintosh 1
#endif

#ifdef macintosh
#include <console.h>
#include <unix.h>
#endif

#include <iostream>

#include <stdio.h>
#include <errno.h>
#include <math.h>
#include <string.h>
#include <stdlib.h>

#include "planet.h"
#include "map.h"

int BLACK = 0;
int WHITE = 1;
int BACK = 2;
int GRID = 3;
int OUTLINE1 = 4;
int OUTLINE2 = 5;
int LOWEST = 6;
int SEA = 7;
int LAND = 8;
int HIGHEST = 9;

int debug = 0;

char view;

int nocols = 65536;

int rtable[65536], gtable[65536], btable[65536];

/* Supported output file types:
    BMP - Windows Bit MaPs
    PPM - Portable Pix Maps
    XPM - X-windows Pix Maps
 */

typedef enum ftype {
    bmp,
    ppm,
    xpm
}
ftype;

ftype file_type = bmp;

char* file_ext(ftype file_type)
{
    switch (file_type) {
    case bmp:
        return (".bmp");
    case ppm:
        return (".ppm");
    case xpm:
        return (".xpm");
    default:
        return ("");
    }
}

/* Character table for XPM output */

char letters[64] = {
    '@','$','.',',',':',';','-','+','=','#','*','&','A','B','C','D',
    'E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T',
    'U','V','W','X','Y','Z','a','b','c','d','e','f','g','h','i','j',
    'k','l','m','n','o','p','q','r','s','t','u','v','w','x','y','z'
};

#define DEG2RAD 0.0174532918661 /* pi/180 */


#if 0
extern double ssa,ssb,ssc,ssd, ssas,ssbs,sscs,ssds,
       ssax,ssay,ssaz, ssbx,ssby,ssbz, sscx,sscy,sscz, ssdx,ssdy,ssdz;
extern double M;   /* initial altitude (slightly below sea level) */
extern int Depth; /* depth of subdivisions */
extern double r1,r2,r3,r4; /* seeds */
extern double dd1;  /* weight for altitude difference */
extern double dd2; /* weight for distance */
extern double POW;  /* power for distance function */

double rand2(double p, double q); /* random number generator taking two seeds */
#endif

double log_2(double x);

double longi,lat,scale;
double vgrid, hgrid;

int Width = 800, Height = 600; /* default map size */

unsigned short **col;  /* colour array */
double **alt;  /* altitude array */
int **heights;         /* heightfield array */
cartPt **pt;
int cl0[60][30]; /* search map */

int do_outline = 0;  /* if 1, draw coastal outline */
int do_bw = 0;       /* if 1, reduce map to black outline on white */
int contourstep = 0; /* if >0, # of colour steps between contour lines */
int *outx, *outy;

int doshade = 0;
int shade;
unsigned short **shades; /* shade array */
double shade_angle = 150.0; /* angle of "light" on bumpmap */
double shade_angle2 = 20.0; /* with daylight shading, these two are
			       longitude/latitude */

double cla, sla, clo, slo;

double increment = 0.00000001;

int best = 500000;
int weight[30];


int planetMain(int ac, char **av);

void readcolors(char* colorsname);
void makeoutline(int do_bw);
void readmap();
void smoothshades();
void Mercator();
void peter();
void squarep();
void mollweide();
void Sinusoid();
void stereo();
void orthographic();
void gnomonic();
void azimuth();
void conical();
void heightfield();
void search();
int alt2color(double alt);
void printppm(FILE *outfile); /* prints picture in PPM (portable pixel map) format */
void printppmBW(FILE *outfile); /* prints picture in b/w PPM format */
void printbmp(FILE *outfile); /* prints picture in BMP format */
void printbmpBW(FILE *outfile); /* prints picture in b/w BMP format */
char *nletters(int n, int c);
void printxpm(FILE *outfile); /* prints picture in XPM (X-windows pixel map) format */
void printxpmBW(FILE *outfile); /* prints picture in XPM (X-windows pixel map) format */
void printheights(FILE *outfile); /* prints heightfield */
void print_error(const char *filename, const char *ext);
void doShade(int doshade);

void readcolors(char* colorsname)
{
    int crow, cNum = 0, oldcNum, i;
    FILE *colfile = NULL;

    if (NULL == (colfile = fopen(colorsname, "r"))) {
        fprintf(stderr,
                "Cannot open %s\n",
                colorsname);
        exit(1);
    }


    /* Format of colour file is a sequence of lines       */
    /* each consisting of four integers:                  */
    /*   colour_number red green blue                     */
    /* where 0 <= colour_number <= 65535                  */
    /* and 0<= red, green, blue <= 255                    */
    /* The colour numbers must be increasing              */
    /* The first colours have special uses:               */
    /* 0 is usually black (0,0,0)                         */
    /* 1 is usually white (255,255,255)                   */
    /* 2 is the background colour                         */
    /* 3 is used for latitude/longitude grid lines        */
    /* 4 and 5 are used for outlines and contour lines    */
    /* 6 upwards are used for altitudes                   */
    /* Halfway between 6 and the max colour is sea level  */
    /* Shallowest sea is (max+6)/2 and land is above this */
    /* With 65536 colours, (max+6)/2 = 32770              */
    /* Colours between specified are interpolated         */

    for (crow = 0; !feof(colfile); crow++) {
        int	rValue,
            gValue,
            bValue,
            result = 0;

        oldcNum = cNum;  /* remember last colour number */
        result = fscanf(colfile, " %d %d %d %d",
                        &cNum, &rValue, &gValue, &bValue);

        if (result > 0) {
            if (cNum < oldcNum) cNum = oldcNum;
            if (cNum > 65535) cNum = 65535;
            rtable[cNum] = rValue;
            gtable[cNum] = gValue;
            btable[cNum] = bValue;
            /* interpolate colours between oldcNum and cNum */
            for (i = oldcNum+1; i<cNum; i++) {
                rtable[i] = (rtable[oldcNum]*(cNum-i)+rtable[cNum]*(i-oldcNum))
                            / (cNum-oldcNum+1);
                gtable[i] = (gtable[oldcNum]*(cNum-i)+gtable[cNum]*(i-oldcNum))
                            / (cNum-oldcNum+1);
                btable[i] = (btable[oldcNum]*(cNum-i)+btable[cNum]*(i-oldcNum))
                            / (cNum-oldcNum+1);
            }
        }
    }

    nocols = cNum+1;
    if (nocols < 10) nocols = 10;

    HIGHEST = nocols - 1;
    SEA = (HIGHEST+LOWEST)/2;
    LAND = SEA+1;

    for (i = cNum+1; i<nocols; i++) {
        /* fill up rest of colour table with last read colour */
        rtable[i] = rtable[cNum];
        gtable[i] = gtable[cNum];
        btable[i] = btable[cNum];
    }
}

void makeoutline(int do_bw)
{
    int i,j,k,t;

    outx = (int*)calloc(Width*Height,sizeof(int));
    outy = (int*)calloc(Width*Height,sizeof(int));
    k=0;
    for (i=1; i<Width-1; i++)
        for (j=1; j<Height-1; j++)
            if ((col[i][j] >= LOWEST && col[i][j] <= SEA) &&
                (col[i-1][j] >= LAND || col[i+1][j] >= LAND ||
                 col[i][j-1] >= LAND || col[i][j+1] >= LAND ||
                 col[i-1][j-1] >= LAND || col[i-1][j+1] >= LAND ||
                 col[i+1][j-1] >= LAND || col[i+1][j+1] >= LAND)) {
                /* if point is sea and any neighbour is not, add to outline */
                outx[k] = i;
                outy[k++] = j;
            }

    if (contourstep>0) {

        for (i=1; i<Width-1; i++)
            for (j=1; j<Height-1; j++) {
                t = (col[i][j] - LAND) / contourstep;
                if (t>=0 &&
                    ((col[i-1][j]-LAND) / contourstep > t ||
                     (col[i+1][j]-LAND) / contourstep > t ||
                     (col[i][j-1]-LAND) / contourstep > t ||
                     (col[i][j+1]-LAND) / contourstep > t)) {
                    /* if point is at countour line and any neighbour is higher */
                    outx[k] = i;
                    outy[k++] = j;
                }
            }
    }
    if (do_bw) /* if outline only, clear colours */
        for (i=0; i<Width; i++)
            for (j=0; j<Height; j++) {
                if (col[i][j] >= LOWEST)
                    col[i][j] = WHITE;
                else col[i][j] = BLACK;
            }
    /* draw outline (in black if outline only) */
    while (k-->0) {
        if (do_bw) t = BLACK;
        else if (contourstep == 0 || col[outx[k]][outy[k]]<LAND ||
                 ((col[outx[k]][outy[k]]-LAND)/contourstep)%2 == 1)
            t = OUTLINE1;
        else t = OUTLINE2;
        col[outx[k]][outy[k]] = t;
    }
}

void readmap()
{
    int i,j;
    double y;
    char c;

    Width = 47;
    Height = 21;
    for (j = 0; j < Height; j++) {
        y = 0.5*7.5*(2.0*j-Height+1);
        y = cos(DEG2RAD*y);
        weight[j] = (int)(100.0*y+0.5);
    }
    for (j = 0; j < Height; j+=2) {
        for(i = 0; i < Width ; i+=2) {
            c = getchar();
            switch (c) {
            case '.':
                cl0[i][j] = -8;
                break;
            case ',':
                cl0[i][j] = -4;
                break;
            case ':':
                cl0[i][j] = -2;
                break;
            case ';':
                cl0[i][j] = -1;
                break;
            case '-':
                cl0[i][j] = 0;
                break;
            case '*':
                cl0[i][j] = 1;
                break;
            case 'o':
                cl0[i][j] = 2;
                break;
            case 'O':
                cl0[i][j] = 4;
                break;
            case '@':
                cl0[i][j] = 8;
                break;
            default:
                printf("Wrong map symbol: %c\n",c);
            }
            if (i>0) cl0[i-1][j] = (cl0[i][j]+cl0[i-2][j])/2;
        }
        c = getchar();
        if (c!='\n') printf("Wrong map format: %c\n",c);
    }
    for (j = 1; j < Height; j+=2)
        for(i = 0; i < Width ; i++)
            cl0[i][j] = (cl0[i][j-1]+cl0[i][j+1])/2;
}


void smoothshades()
{
    int i,j;

    for (i=0; i<Width-2; i++)
        for (j=0; j<Height-2; j++)
            shades[i][j] = (4*shades[i][j]+2*shades[i][j+1]
                            +2*shades[i+1][j]+shades[i+1][j+1]+4)/9;
}

void Mercator()
{
    std::cerr << "start Mercator()" << std::endl;
    mercator m;
    //Height = 200;
    //Width = 400;
    m.setHeight(Height);
    m.setWidth(Width);
    m.setScale(scale);
    m.setLongitude(longi);
    m.setLatitude(lat);
    planet p;

    int depth = 4 * log_2(Height);
    for (int j = 0; j < Height; j++) {
        for (int i = 0; i < Width ; i++) {
            pt[i][j] = m.convert(i,j);
            alt[i][j] = p.elevation(pt[i][j].x,pt[i][j].y,pt[i][j].z, depth);
            sphericalPt pt = m.sconvert(i,j);
            //std::cerr << "long = " << pt.longitude << " lat = " << pt.latitude << std::endl;
            col[i][j] = p.elevation(pt.longitude,pt.latitude,depth);
            //col[i][j] = alt2color(alt[i][j]);
            if (doshade > 0) shades[i][j] = shade;
        }
    }
    std::cerr << "end Mercator()" << std::endl;
}

void Sinusoid()
{
    std::cerr << "start Sinusoid()" << std::endl;
    sinusoid s;
    s.setHeight(Height);
    s.setWidth(Width);
    s.setScale(scale);
    s.setLongitude(longi);
    s.setLatitude(lat);

    for (int j = 0; j < Height; j++) {
        for (int i = 0; i < Width ; i++) {
            col[i][j] = BACK;
        }
    }
}

void search(double seed)
{
    double y,cos2,theta1,scale1;
    double y2,cos22,theta12;
    int i,j,k,l,c,c1,c2,c3, errcount, errcount1;
    planet p;
    p.seed(seed);

    for (j = 0; j < Height; j++) {
        y = 0.5*7.5*(2.0*j-Height+1);
        y = sin(DEG2RAD*y);
        scale1 = Width/Height/sqrt(1.0-y*y)/PI;
        cos2 = sqrt(1.0-y*y);
        y2 = 0.5*7.5*(2.0*j-Height+1.5);
        y2 = sin(DEG2RAD*y2);
        cos22 = sqrt(1.0-y2*y2);
        int depth = 3*((int)(log_2(scale1*Height)))+6;
        for (i = 0; i < Width ; i++) {
            theta1 = -0.5*PI+PI*(2.0*i-Width)/Width;
            theta12 = -0.5*PI+PI*(2.0*i+0.5-Width)/Width;
            c = 128+1000*p.elevation(cos(theta1)*cos2,y,-sin(theta1)*cos2, depth);
            c1 = 128+1000*p.elevation(cos(theta12)*cos2,y,-sin(theta12)*cos2, depth);
            c2 = 128+1000*p.elevation(cos(theta1)*cos22,y2,-sin(theta1)*cos22, depth);
            c3 = 128+1000*p.elevation(cos(theta12)*cos22,y2,-sin(theta12)*cos22, depth);
            c = (c+c1+c2+c3)/4.0;
            if (c<0) c = 0;
            if (c>255) c = 255;
            col[i][j] = c;
        }
    }
    for (k=0; k<Width; k++) {
        for (l=-20; l<=20; l+=2) {
            errcount = 0;
            for (j = 0; j < Height; j++) {
                errcount1 = 0;
                for(i = 0; i < Width ; i++) {
                    if (cl0[i][j]<0 && col[(i+k)%Width][j] > 128-l)
                        errcount1-=cl0[i][j];
                    if (cl0[i][j]>0 && col[(i+k)%Width][j] <= 128-l)
                        errcount1+=cl0[i][j];
                }
                errcount += weight[j]*errcount1;
            }

            if (errcount < best) {
                printf("Errors: %d, parameters: -l %.1f\n",
                       errcount,(360.0*k)/(Width+1));
                best = errcount;
                for (j = 0; j < Height; j++) {
                    for(i = 0; i < Width ; i++)
                        if (col[(i+k)%Width][j] <= 128-l) putchar('.');
                        else putchar('O');
                    putchar('\n');
                }
                fflush(stdout);
            }
        }
    }
}

int alt2color(double alt)
{
    int colour;

    /* calculate colour */
    if (alt <=0.) { /* if below sea level then */
        colour = SEA+(int)((SEA-LOWEST+1)*(10*alt));
        if (colour<LOWEST) colour = LOWEST;
    } else {
        if (alt >= 0.1) /* if high then */
            colour = HIGHEST;
        else {
            colour = LAND+(int)((HIGHEST-LAND+1)*(10*alt));
            if (colour>HIGHEST) colour = HIGHEST;
        }
    }
    return(colour);
}

void printppm(FILE *outfile) /* prints picture in PPM (portable pixel map) format */
{
    int i,j,c,s;

    fprintf(outfile,"P6\n");
    fprintf(outfile,"#fractal planet image\n");
    fprintf(outfile,"%d %d 255\n",Width,Height);

    if (doshade) {
        for (j=0; j<Height; j++) {
            for (i=0; i<Width; i++) {
                s =shades[i][j];
                c = s*rtable[col[i][j]]/150;
                if (c>255) c=255;
                putc(c,outfile);
                c = s*gtable[col[i][j]]/150;
                if (c>255) c=255;
                putc(c,outfile);
                c = s*btable[col[i][j]]/150;
                if (c>255) c=255;
                putc(c,outfile);
            }
        }
    } else {
        for (j=0; j<Height; j++)
            for (i=0; i<Width; i++) {
                putc(rtable[col[i][j]],outfile);
                putc(gtable[col[i][j]],outfile);
                putc(btable[col[i][j]],outfile);
            }
    }
    fclose(outfile);
}

void printppmBW(FILE *outfile) /* prints picture in b/w PPM format */
{
    int i,j,c;

    fprintf(outfile,"P6\n");
    fprintf(outfile,"#fractal planet image\n");
    fprintf(outfile,"%d %d 1\n",Width,Height);

    for (j=0; j<Height; j++)
        for (i=0; i<Width; i++) {
            if (col[i][j] < WHITE)
                c=0;
            else c=1;
            putc(c,outfile);
            putc(c,outfile);
            putc(c,outfile);
        }
    fclose(outfile);
}

void printbmp(FILE *outfile) /* prints picture in BMP format */
{
    int i,j,c,s, W1;

    fprintf(outfile,"BM");

    W1 = (3*Width+3);
    W1 -= W1 % 4;
    s = 54+W1*Height; /* file size */
    putc(s&255,outfile);
    putc((s>>8)&255,outfile);
    putc((s>>16)&255,outfile);
    putc(s>>24,outfile);

    putc(0,outfile);
    putc(0,outfile);
    putc(0,outfile);
    putc(0,outfile);

    putc(54,outfile); /* offset to data */
    putc(0,outfile);
    putc(0,outfile);
    putc(0,outfile);

    putc(40,outfile); /* size of infoheader */
    putc(0,outfile);
    putc(0,outfile);
    putc(0,outfile);

    putc(Width&255,outfile);
    putc((Width>>8)&255,outfile);
    putc((Width>>16)&255,outfile);
    putc(Width>>24,outfile);

    putc(Height&255,outfile);
    putc((Height>>8)&255,outfile);
    putc((Height>>16)&255,outfile);
    putc(Height>>24,outfile);

    putc(1,outfile);  /* no. of planes = 1 */
    putc(0,outfile);

    putc(24,outfile);  /* bpp */
    putc(0,outfile);

    putc(0,outfile); /* no compression */
    putc(0,outfile);
    putc(0,outfile);
    putc(0,outfile);

    putc(0,outfile); /* image size (unspecified) */
    putc(0,outfile);
    putc(0,outfile);
    putc(0,outfile);

    putc(0,outfile); /* h. pixels/m */
    putc(32,outfile);
    putc(0,outfile);
    putc(0,outfile);

    putc(0,outfile); /* v. pixels/m */
    putc(32,outfile);
    putc(0,outfile);
    putc(0,outfile);

    putc(0,outfile); /* colours used (unspecified) */
    putc(0,outfile);
    putc(0,outfile);
    putc(0,outfile);


    putc(0,outfile); /* important colours (all) */
    putc(0,outfile);
    putc(0,outfile);
    putc(0,outfile);

    if (doshade) {
        for (j=Height-1; j>=0; j--) {
            for (i=0; i<Width; i++) {
                s =shades[i][j];
                c = s*btable[col[i][j]]/150;
                if (c>255) c=255;
                putc(c,outfile);
                c = s*gtable[col[i][j]]/150;
                if (c>255) c=255;
                putc(c,outfile);
                c = s*rtable[col[i][j]]/150;
                if (c>255) c=255;
                putc(c,outfile);
            }
            for (i=3*Width; i<W1; i++) putc(0,outfile);
        }
    } else {
        for (j=Height-1; j>=0; j--) {
            for (i=0; i<Width; i++) {
                putc(btable[col[i][j]],outfile);
                putc(gtable[col[i][j]],outfile);
                putc(rtable[col[i][j]],outfile);
            }
            for (i=3*Width; i<W1; i++) putc(0,outfile);
        }
    }
    fclose(outfile);
}

void printbmpBW(FILE *outfile) /* prints picture in b/w BMP format */
{
    int i,j,c,s, W1;

    fprintf(outfile,"BM");

    W1 = (Width+31);
    W1 -= W1 % 32;
    s = 62+(W1*Height)/8; /* file size */
    putc(s&255,outfile);
    putc((s>>8)&255,outfile);
    putc((s>>16)&255,outfile);
    putc(s>>24,outfile);

    putc(0,outfile);
    putc(0,outfile);
    putc(0,outfile);
    putc(0,outfile);

    putc(62,outfile); /* offset to data */
    putc(0,outfile);
    putc(0,outfile);
    putc(0,outfile);

    putc(40,outfile); /* size of infoheader */
    putc(0,outfile);
    putc(0,outfile);
    putc(0,outfile);

    putc(Width&255,outfile);
    putc((Width>>8)&255,outfile);
    putc((Width>>16)&255,outfile);
    putc(Width>>24,outfile);

    putc(Height&255,outfile);
    putc((Height>>8)&255,outfile);
    putc((Height>>16)&255,outfile);
    putc(Height>>24,outfile);

    putc(1,outfile);  /* no. of planes = 1 */
    putc(0,outfile);

    putc(1,outfile);  /* bpp */
    putc(0,outfile);

    putc(0,outfile); /* no compression */
    putc(0,outfile);
    putc(0,outfile);
    putc(0,outfile);

    putc(0,outfile); /* image size (unspecified) */
    putc(0,outfile);
    putc(0,outfile);
    putc(0,outfile);

    putc(0,outfile); /* h. pixels/m */
    putc(32,outfile);
    putc(0,outfile);
    putc(0,outfile);

    putc(0,outfile); /* v. pixels/m */
    putc(32,outfile);
    putc(0,outfile);
    putc(0,outfile);

    putc(2,outfile); /* colours used */
    putc(0,outfile);
    putc(0,outfile);
    putc(0,outfile);


    putc(2,outfile); /* important colours (2) */
    putc(0,outfile);
    putc(0,outfile);
    putc(0,outfile);

    putc(0,outfile); /* colour 0 = black */
    putc(0,outfile);
    putc(0,outfile);
    putc(0,outfile);

    putc(255,outfile); /* colour 1 = white */
    putc(255,outfile);
    putc(255,outfile);
    putc(255,outfile);

    for (j=Height-1; j>=0; j--)
        for (i=0; i<W1; i+=8) {
            if (i<Width && col[i][j] >= WHITE)
                c=128;
            else c=0;
            if (i+1<Width && col[i+1][j] >= WHITE)
                c+=64;
            if (i+2<Width && col[i+2][j] >= WHITE)
                c+=32;
            if (i+3<Width && col[i+3][j] >= WHITE)
                c+=16;
            if (i+4<Width && col[i+4][j] >= WHITE)
                c+=8;
            if (i+5<Width && col[i+5][j] >= WHITE)
                c+=4;
            if (i+6<Width && col[i+6][j] >= WHITE)
                c+=2;
            if (i+7<Width && col[i+7][j] >= WHITE)
                c+=1;
            putc(c,outfile);
        }
    fclose(outfile);
}

char *nletters(int n, int c)
{
    int i;
    static char buffer[8];

    buffer[n] = '\0';

    for (i = n-1; i >= 0; i--) {
        buffer[i] = letters[c & 0x001F];
        c >>= 5;
    }

    return buffer;
}

void printxpm(FILE *outfile) /* prints picture in XPM (X-windows pixel map) format */
{
    int x,y,i,nbytes;

    x = nocols - 1;
    for (nbytes = 0; x != 0; nbytes++)
        x >>= 5;

    fprintf(outfile,"/* XPM */\n");
    fprintf(outfile,"static char *xpmdata[] = {\n");
    fprintf(outfile,"/* width height ncolors chars_per_pixel */\n");
    fprintf(outfile,"\"%d %d %d %d\",\n", Width, Height, nocols, nbytes);
    fprintf(outfile,"/* colors */\n");
    for (i = 0; i < nocols; i++)
        fprintf(outfile,"\"%s c #%2.2X%2.2X%2.2X\",\n",
                nletters(nbytes, i), rtable[i], gtable[i], btable[i]);

    fprintf(outfile,"/* pixels */\n");
    for (y = 0 ; y < Height; y++) {
        fprintf(outfile,"\"");
        for (x = 0; x < Width; x++)
            fprintf(outfile, "%s", nletters(nbytes, col[x][y]));
        fprintf(outfile,"\",\n");
    }
    fprintf(outfile,"};\n");

    fclose(outfile);
}

void printxpmBW(FILE *outfile) /* prints picture in XPM (X-windows pixel map) format */
{
    int x,y,nbytes;

    x = nocols - 1;
    nbytes = 1;

    fprintf(outfile,"/* XPM */\n");
    fprintf(outfile,"static char *xpmdata[] = {\n");
    fprintf(outfile,"/* width height ncolors chars_per_pixel */\n");
    fprintf(outfile,"\"%d %d %d %d\",\n", Width, Height, 2, nbytes);
    fprintf(outfile,"/* colors */\n");

    fprintf(outfile,"\". c #FFFFFF\",\n");
    fprintf(outfile,"\"X c #000000\",\n");

    fprintf(outfile,"/* pixels */\n");
    for (y = 0 ; y < Height; y++) {
        fprintf(outfile,"\"");
        for (x = 0; x < Width; x++)
            fprintf(outfile, "%s",
                    (col[x][y] < WHITE)
                    ? "X" : ".");
        fprintf(outfile,"\",\n");
    }
    fprintf(outfile,"};\n");

    fclose(outfile);
}

void printheights(FILE *outfile) /* prints heightfield */
{
    int i,j;

    for (j=0; j<Height; j++) {
        for (i=0; i<Width; i++)
            fprintf(outfile,"%d ",heights[i][j]);
        putc('\n',outfile);
    }
    fclose(outfile);
}

double log_2(double x)
{
    return(log(x)/log(2.0));
}

void print_error(const char *filename, const char *ext)
{
    fprintf(stderr,"Usage: planet [options]\n\n");
    fprintf(stderr,"options:\n");
    fprintf(stderr,"  -?                (or any illegal option) Output this text\n");
    fprintf(stderr,"  -s seed           Specifies seed as number between 0.0 and 1.0\n");
    fprintf(stderr,"  -w width          Specifies width in pixels, default = 800\n");
    fprintf(stderr,"  -h height         Specifies height in pixels, default = 600\n");
    fprintf(stderr,"  -m magnification  Specifies magnification, default = 1.0\n");
    fprintf(stderr,"  -o output_file    Specifies output file, default is %s%s\n",
            filename, ext);
    fprintf(stderr,"  -l longitude      Specifies longitude of centre in degrees, default = 0.0\n");
    fprintf(stderr,"  -L latitude       Specifies latitude of centre in degrees, default = 0.0\n");
    fprintf(stderr,"  -g gridsize       Specifies vertical gridsize in degrees, default = 0.0 (no grid)\n");
    fprintf(stderr,"  -G gridsize       Specifies horisontal gridsize in degrees, default = 0.0 (no grid)\n");
    fprintf(stderr,"  -i init_alt       Specifies initial altitude (default = -0.02)\n");
    fprintf(stderr,"  -c                Colour depends on latitude (default: only altitude)\n");
    fprintf(stderr,"  -C file           Read colour definitions from file\n");
    fprintf(stderr,"  -O                Produce a black and white outline map\n");
    fprintf(stderr,"  -E                Trace the edges of land in black on colour map\n");
    fprintf(stderr,"  -B                Use ``bumpmap'' shading\n");
    fprintf(stderr,"  -b                Use ``bumpmap'' shading on land only\n");
    fprintf(stderr,"  -d                Use ``daylight'' shading\n");
    fprintf(stderr,"  -a angle	      Angle of ``light'' in bumpmap shading\n");
    fprintf(stderr,"                    or longitude of sun in daylight shading\n");
    fprintf(stderr,"  -A latitude	      Latitude of sun in daylight shading\n");
    fprintf(stderr,"  -P                Use PPM file format (default is BMP)\n");
    fprintf(stderr,"  -x                Use XPM file format (default is BMP)\n");
    fprintf(stderr,"  -V number         Distance contribution to variation (default = 0.03)\n");
    fprintf(stderr,"  -v number         Altitude contribution to variation (default = 0.4)\n");
    fprintf(stderr,"  -pprojection      Specifies projection: m = Mercator (default)\n");
    fprintf(stderr,"                                          p = Peters\n");
    fprintf(stderr,"                                          q = Square\n");
    fprintf(stderr,"                                          s = Stereographic\n");
    fprintf(stderr,"                                          o = Orthographic\n");
    fprintf(stderr,"                                          g = Gnomonic\n");
    fprintf(stderr,"                                          a = Area preserving azimuthal\n");
    fprintf(stderr,"                                          c = Conical (conformal)\n");
    fprintf(stderr,"                                          M = Mollweide\n");
    fprintf(stderr,"                                          S = Sinusoidal\n");
    fprintf(stderr,"                                          h = Heightfield\n");
    fprintf(stderr,"                                          f = Find match, see manual\n");
    exit(0);
}

/* With the -pf option a map must be given on standard input.  */
/* This map is 11 lines of 24 characters. The characters are:  */
/*    . : very strong preference for water (value=8)	       */
/*    , : strong preference for water (value=4)		       */
/*    : : preference for water (value=2)		       */
/*    ; : weak preference for water (value=1)		       */
/*    - : don't care (value=0)				       */
/*    * : weak preference for land (value=1)		       */
/*    o : preference for land (value=2)			       */
/*    O : strong preference for land (value=4)		       */
/*    @ : very strong preference for land (value=8)	       */
/*							       */
/* Each point on the map corresponds to a point on a 15\B0 grid. */
/*							       */
/* The program tries seeds starting from the specified and     */
/* successively outputs the seed (and rotation) of the best    */
/* current match, together with a small map of this.	       */
/* This is all ascii, no bitmap is produced.		       a*/




int planetMain(int ac, char **av)
{
    int i;
    FILE *outfile;
    char filename[256] = "planet-map";
    char colorsname[256] = "Olsson.col";
    int do_file = 0;


#ifdef macintosh
    _ftype = 'TEXT';
    _fcreator ='ttxt';

    ac = ccommand (&av);
    debug = 1;
    do_file = 1;
#endif

    longi = 0.0;
    lat = 0.0;
    scale = 1.0;
    view = 'm';
    vgrid = hgrid = 0.0;
    outfile = stdout;

    for (i = 1; i<ac; i++) {
        if (av[i][0] == '-') {
            switch (av[i][1]) {
            case 'X' :
                debug = 1;
                break;
            case 'V' :
                //sscanf(av[++i],"%lf",&dd2);
                break;
            case 'v' :
                //sscanf(av[++i],"%lf",&dd1);
                break;
            case 's' :
                //sscanf(av[++i],"%lf",&rseed);
                break;
            case 'w' :
                sscanf(av[++i],"%d",&Width);
                break;
            case 'h' :
                sscanf(av[++i],"%d",&Height);
                break;
            case 'm' :
                sscanf(av[++i],"%lf",&scale);
                break;
            case 'o' :
                sscanf(av[++i],"%s",filename);
                do_file = 1;
                break;
            case 'x' :
                file_type =xpm;
                break;
            case 'C' :
                sscanf(av[++i],"%s",colorsname);
                break;
            case 'l' :
                sscanf(av[++i],"%lf",&longi);
                break;
            case 'L' :
                sscanf(av[++i],"%lf",&lat);
                break;
            case 'g' :
                sscanf(av[++i],"%lf",&vgrid);
                break;
            case 'G' :
                sscanf(av[++i],"%lf",&hgrid);
                break;
            case 'O' :
                do_outline = 1;
                do_bw = 1;
                if (strlen(av[i])>2)
                    sscanf(av[i],"-O%d",&contourstep);
                break;
            case 'E' :
                do_outline = 1;
                if (strlen(av[i])>2)
                    sscanf(av[i],"-E%d",&contourstep);
                break;
            case 'B' :
                doshade = 1;
                break;
            case 'b' :
                doshade = 2;
                break;
            case 'd' :
                doshade = 3;
                break;
            case 'P' :
                file_type = ppm;
                break;
            case 'a' :
                sscanf(av[++i],"%lf",&shade_angle);
                break;
            case 'A' :
                sscanf(av[++i],"%lf",&shade_angle2);
                break;
            case 'i' :
                //sscanf(av[++i],"%lf",&M);
                break;
            case 'p' :
                if (strlen(av[i])>2) view = av[i][2];
                else view = av[++i][0];
                switch (view) {
                case 'm' :
                case 'p' :
                case 'q' :
                case 's' :
                case 'o' :
                case 'g' :
                case 'a' :
                case 'c' :
                case 'M' :
                case 'S' :
                case 'h' :
                case 'f' :
                    break;
                default:
                    fprintf(stderr,"Unknown projection: %s\n",av[i]);
                    print_error(do_file ? filename : "standard output",
                                !do_file ? "" : file_ext(file_type));
                }
                break;
            default:
                fprintf(stderr,"Unknown option: %s\n",av[i]);
                print_error(do_file ? filename : "standard output",
                            !do_file ? "" : file_ext(file_type));
            }
        } else {
            fprintf(stderr,"Unknown option: %s\n\n",av[i]);
            print_error(do_file ? filename : "standard output",
                        !do_file ? "" : file_ext(file_type));
        }
    }

    readcolors(colorsname);

    if (do_file &&'\0' != filename[0]) {
        if (strchr (filename, '.') == 0)
            strcpy(&(filename[strlen(filename)]), file_ext(file_type));

#ifdef macintosh
        switch (file_type) {
        case bmp:
            _ftype = 'BMPf';
            break;
        case ppm:
            _ftype = 'PPGM';
            break;
        case xpm:
            _ftype = 'TEXT';
            break;
        }

        _fcreator ='GKON';
#endif

        outfile = fopen(filename,"wb");

#ifdef macintosh
        _ftype = 'TEXT';
        _fcreator ='ttxt';
#endif

        if (outfile == NULL) {
            fprintf(stderr,
                    "Could not open output file %s, error code = %d\n",
                    filename, errno);
            exit(0);
        }
    } else
        outfile = stdout;

    if (longi>180) longi -= 360;
    longi = longi*DEG2RAD;
    lat = lat*DEG2RAD;

    sla = sin(lat);
    cla = cos(lat);
    slo = sin(longi);
    clo = cos(longi);

    if (view == 'f') readmap();

    if (view == 'h') {
        heights = (int**)calloc(Width,sizeof(int*));
        if (heights == 0) {
            fprintf(stderr, "Memory allocation failed.");
            exit(1);
        }
        for (i=0; i<Width; i++) {
            heights[i] = (int*)calloc(Height,sizeof(int));
            if (heights[i] == 0) {
                fprintf(stderr,
                        "Memory allocation failed at %d out of %d heights\n",
                        i+1,Width);
                exit(1);
            }
        }
    }

    alt = new double*[Width];
    for(i=0; i<Width; i++) {
        alt[i] = new double[Height];
    }

    col = (unsigned short**)calloc(Width,sizeof(unsigned short*));
    if (col == 0) {
        fprintf(stderr, "Memory allocation failed.");
        exit(1);
    }
    for (i=0; i<Width; i++) {
        col[i] = (unsigned short*)calloc(Height,sizeof(unsigned short));
        if (col[i] == 0) {
            fprintf(stderr,
                    "Memory allocation failed at %d out of %d cols\n",
                    i+1,Width);
            exit(1);
        }
    }

    if (doshade>0) {
        shades = (unsigned short**)calloc(Width,sizeof(unsigned short*));
        if (shades == 0) {
            fprintf(stderr, "Memory allocation failed.");
            exit(1);
        }
        for (i=0; i<Width; i++) {
            shades[i] = (unsigned short*)calloc(Height,sizeof(unsigned short));
            if (shades[i] == 0) {
                fprintf(stderr,
                        "Memory allocation failed at %d out of %d shades\n",
                        i,Width);
                exit(1);
            }
        }
    }

    pt = new cartPt*[Width];
    if (pt == 0) {
        fprintf(stderr, "Memory allocation failed.");
        exit(1);
    }
    for (i=0; i<Width; i++) {
        pt[i] = new cartPt[Height];
    }

    if (view == 'c') {
        if (lat == 0) view = 'm';
        /* Conical approaches mercator when lat -> 0 */
        if (abs(lat) >= PI - 0.000001) view = 's';
        /* Conical approaches stereo when lat -> +/- 90 */
    }


    if (debug && (view != 'f'))
        fprintf(stderr, "+----+----+----+----+----+\n");

    switch (view) {

    case 'm': /* Mercator projection */
        Mercator();
        break;

    case 'S': /* Sinusoid projection (area preserving) */
        Sinusoid();
        break;

    case 'f': /* Search */
        double s = 0.0;
        while (1) {
            search(s);
            s+=increment;
        }
    }

    if (debug && (view != 'f'))
        fprintf(stderr, "+----+----+----+----+----+\n");

    if (do_outline) makeoutline(do_bw);

    if (vgrid != 0.0) { /* draw longitudes */
        int i,j;
        for (i=0; i<Width-1; i++)
            for (j=0; j<Height-1; j++) {
                double t;
                int g = 0;
                if (fabs(pt[i][j].y)==1) g=1;
                else {
                    t = floor((atan2(pt[i][j].x,pt[i][j].z)*180/PI+360)/vgrid);
                    if (t != floor((atan2(pt[i+1][j].x,pt[i+1][j].z)*180/PI+360)/vgrid))
                        g=1;
                    if (t != floor((atan2(pt[i][j+1].x,pt[i][j+1].z)*180/PI+360)/vgrid))
                        g=1;
                }
                if (g) {
                    col[i][j] = GRID;
                    if (doshade>0) shades[i][j] = 255;
                }
            }
    }

    if (hgrid != 0.0) { /* draw latitudes */
        int i,j;
        for (i=0; i<Width-1; i++)
            for (j=0; j<Height-1; j++) {
                double t;
                int g = 0;
                t = floor((asin(pt[i][j].y)*180/PI+360)/hgrid);
                if (t != floor((asin(pt[i+1][j].y)*180/PI+360)/hgrid))
                    g=1;
                if (t != floor((asin(pt[i][j+1].y)*180/PI+360)/hgrid))
                    g=1;
                if (g) {
                    col[i][j] = GRID;
                    if (doshade>0) shades[i][j] = 255;
                }
            }
    }

    if (doshade>0) smoothshades();

    if (debug)
        fprintf(stderr, "\n");

    /* plot picture */
    switch (file_type) {
    case ppm:
        if (do_bw) printppmBW(outfile);
        else if (view != 'h') printppm(outfile);
        else printheights(outfile);
        break;
    case xpm:
        if (do_bw) printxpmBW(outfile);
        else if (view != 'h') printxpm(outfile);
        else printheights(outfile);
        break;
    case bmp:
        if (do_bw) printbmpBW(outfile);
        else if (view != 'h') printbmp(outfile);
        else printheights(outfile);
        break;
    }

    return(0);
}


int main(int argc, char **argv)
{
    return(planetMain(argc, argv));
}
