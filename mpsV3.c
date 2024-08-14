#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <termios.h>
#include <stdbool.h>
#include <stdint.h>
#include <curl/curl.h>

#define UART_DEVICE "/dev/ttyS0"
#define BAUD_RATE B38400
#define SAMPCNT 1
#define READBUF 70

int uart_fd;
uint8_t cmd_meas[] = {0x61, 0x00, 0x01, 0x00, 0x00, 0x00, 0x57, 0x93, 0x02};
uint8_t cmd_data[] = {0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0xed, 0x76};
uint8_t read_buf[READBUF];
uint8_t pcycle = 0;

void logInfo(const char* message) {
    printf("%s\n", message);
}

float bytes_to_float(uint8_t b0, uint8_t b1, uint8_t b2, uint8_t b3) {
    float f;
    uint32_t bytes = (b0 << 24) | (b1 << 16) | (b2 << 8) | b3;
    memcpy(&f, &bytes, sizeof(f));
    return f;
}

void save_data_to_json(float temp, float pres, float CH4_conc) {
    FILE *file = fopen("sensor_data.json", "w");
    if (file == NULL) {
        perror("Error opening file");
        return;
    }

    fprintf(file, "{\n\t\"temperature\": %.2f,\n\t\"pressure\": %.2f,\n\t\"Methane_gas_concentration\": %.2f\n}\n",
            temp, pres, CH4_conc);
    fclose(file);
}

void upload_data_to_thingsboard() {
    CURL *curl;
    CURLcode res;
    FILE *file;
    long file_size;
    char *data;
    char url[] = "http://frontgate.tplinkdns.com:8080/api/v1/wK1ks4U4doKm8CSJEJmR/telemetry";
    
    // open file
    printf("Opening file sensor_data.json...\n");
    file = fopen("sensor_data.json", "rb");
    if (file == NULL) {
        perror("Error opening file");
        return;
    }
    
    // get file size
    printf("Getting file size...\n");
    fseek(file, 0, SEEK_END);
    file_size = ftell(file);
    fseek(file, 0, SEEK_SET);
    
    if (file_size < 0) {
        perror("Error getting file size");
        fclose(file);
        return;
    }
    printf("File size: %ld bytes\n", file_size);
    
    // Allocate file to memory
    printf("Allocating memory...\n");
    data = (char *)malloc(file_size + 1);
    if (data == NULL) {
        perror("Error allocating memory");
        fclose(file);
        return;
    }
    
    printf("Reading file content...\n");
    size_t read_size = fread(data, 1, file_size, file);
    if (read_size != file_size) {
        perror("Error reading file");
        free(data);
        fclose(file);
        return;
    }
    fclose(file);
    data[file_size] = '\0';
    printf("File content: %s\n", data);
    
    // Initialize ibcurl
    printf("Initializing CURL...\n");
    curl_global_init(CURL_GLOBAL_ALL);
    curl = curl_easy_init();
    if(!curl) {
        fprintf(stderr, "Error initializing CURL.\n");
        free(data);
        return;
    }
    
    // set URL
    curl_easy_setopt(curl, CURLOPT_URL, url);
    
    // set HTTP POST request
    curl_easy_setopt(curl, CURLOPT_POST, 1L);
    curl_easy_setopt(curl, CURLOPT_POSTFIELDS, data);
    struct curl_slist *headers = NULL;
    headers = curl_slist_append(headers, "Content-Type: application/json");
    if (!headers) {
        fprintf(stderr, "Error setting HTTP header.\n");
        curl_easy_cleanup(curl);
        free(data);
        return;
    }
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
    
    // execute request
    printf("Performing CURL request...\n");
    res = curl_easy_perform(curl);
    if(res != CURLE_OK) {
        fprintf(stderr, "curl_easy_perform() failed: %s\n", curl_easy_strerror(res));
    } else {
        printf("CURL request successful.\n");
    }
    
    // clean & free
    curl_slist_free_all(headers);
    curl_easy_cleanup(curl);
    curl_global_cleanup();
    
    free(data);
}

bool sensor_start() {
    int tries = 5;
    bool success = false;
    int rcnt = 0;

    while ((tries > 0) && (!success)) {
        write(uart_fd, cmd_meas, sizeof(cmd_meas));//Perform measurement request
        read_buf[0] = 0xff;
        read_buf[1] = 0xff;
        rcnt = read(uart_fd, read_buf, sizeof(read_buf));

        if ((rcnt > 2) && (read_buf[0] == 0x61) && (read_buf[1] == 0) && (!((read_buf[6] == 0x57) && (read_buf[7] == 0x93) && (read_buf[8] == 0x02)))) {
            logInfo("[DONE] Valid response from Sensor.");
            success = true;
        } else {
            logInfo("[WAIT] No valid response from Sensor.");
            sleep(1); 
        }
        tries--;
    }
    return success;
}

bool sensor_read(uint8_t* tx_data, size_t* tx_data_size) {
    int tries = 5;
    bool success = false;
    int rcnt;
    uint8_t ccycle;

    while ((tries > 0) && (!success)) {
        write(uart_fd, cmd_data, sizeof(cmd_data));//Get answer request
        read_buf[0] = 0xff;
        read_buf[1] = 0xff;
        rcnt = read(uart_fd, read_buf, sizeof(read_buf));

        if (rcnt > 6) {
            ccycle = read_buf[6];//get the current sending cycle

            if ((read_buf[0] == 0x01) && (read_buf[1] == 0) && (ccycle != pcycle)) {
                logInfo("[DONE] New data from Sensor.");
                pcycle = ccycle;
                success = true;
                tx_data[(*tx_data_size)++] = 'x';
                for (int j = 6; j < rcnt; j += 4) {
                    for (int i = j + 3; i >= j; i--) {
                        tx_data[(*tx_data_size)++] = read_buf[i];
                        }
                }
                float CH4_conc = bytes_to_float(read_buf[13], read_buf[12], read_buf[11], read_buf[10]);
                float temp = bytes_to_float(read_buf[21], read_buf[20], read_buf[19], read_buf[18]);
                float pres = bytes_to_float(read_buf[25], read_buf[24], read_buf[23], read_buf[22]);
                // float relative_humidity = bytes_to_float(read_buf[29], read_buf[28], read_buf[27], read_buf[26]);
                // float absolute_humidity = bytes_to_float(read_buf[33], read_buf[32], read_buf[31], read_buf[30]);
                /*
                float temperature = bytes_to_float(tx_data[13], tx_data[14], tx_data[15], tx_data[16]);
                float pressure = bytes_to_float(tx_data[17], tx_data[18], tx_data[19], tx_data[20]);
                float relative_humidity = bytes_to_float(tx_data[21], tx_data[22], tx_data[23], tx_data[24]);
                float absolute_humidity = bytes_to_float(tx_data[25], tx_data[26], tx_data[27], tx_data[28]);
                */
                
                printf("Temperature: %.2f C\n", temp);
                printf("Pressure: %.2f kPa\n", pres);
                printf("Methane gas concentration: %.2f ppm\n", CH4_conc);
                //printf("Relative Humidity: %.2f %%RH\n", relative_humidity);
                //printf("Absolute Humidity: %.2f g/m3\n", absolute_humidity);
                

                save_data_to_json(temp, pres, CH4_conc);
                
            } else {
                logInfo("[WAIT] Duplicate data from Sensor.");
                sleep(1); 
            }
        } else {
            logInfo("[WAIT] No response from Sensor.");
            sleep(1);
        }

        tries--;
    }
    return success;
}

int main() {
    uint8_t tx_data[READBUF];
    size_t tx_data_size = 0;
    bool boot = true;

    uart_fd = open(UART_DEVICE, O_RDWR | O_NOCTTY | O_NDELAY);
    if (uart_fd == -1) {
        perror("Unable to open UART");
        return 1;
    }

    struct termios options;
    tcgetattr(uart_fd, &options);
    options.c_cflag = BAUD_RATE | CS8 | CLOCAL | CREAD;
    options.c_iflag = IGNPAR;
    options.c_oflag = 0;
    options.c_lflag = 0;
    tcflush(uart_fd, TCIFLUSH);
    tcsetattr(uart_fd, TCSANOW, &options);

    while (1) {
        if (boot) {
            boot = false;
            sleep(3); 
            if (!sensor_start()) {
                logInfo("[FAIL] Sensor failed to initialize 5 times.");
                 return 0;            
                }
        }

        if (!boot) {
            if (!sensor_read(tx_data, &tx_data_size)) {
                logInfo("[FAIL] Sensor failed to produce data 5 times.");
                boot = true;
            }

            if (!boot) {
                upload_data_to_thingsboard();//send data to thingsboard
                sleep(1); 
            }
        }
    }

    close(uart_fd);
    return 0;
}