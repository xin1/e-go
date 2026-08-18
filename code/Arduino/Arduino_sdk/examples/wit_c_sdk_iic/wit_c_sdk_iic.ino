#include <Wire.h>
#include <REG.h>
#include <wit_c_sdk.h>

/*
Test on Arduino Uno. use JY901S sensor

 JY901S           Arduino Uno
  VCC      <--->   5V/3.3V
  SCL      <--->   A5/SCL
  SDA      <--->   A4/SDA
  GND      <--->    GND
*/

#define ACC_UPDATE		0x01
#define GYRO_UPDATE		0x02
#define ANGLE_UPDATE	0x04
#define MAG_UPDATE		0x08
#define READ_UPDATE		0x80
#define MAX_SENSOR_NUM  2
static char s_cDataUpdate = 0, s_cCmd = 0xff;
static uint8_t s_ucSensorAddr[MAX_SENSOR_NUM] = {0};
static uint8_t s_ucSensorNum = 0;

static void CmdProcess(void);
static void AutoScanSensor(void);
static void SensorUartSend(uint8_t *p_data, uint32_t uiSize);
static void CopeSensorData(uint32_t uiReg, uint32_t uiRegNum);
static int32_t IICreadBytes(uint8_t dev, uint8_t reg, uint8_t *data, uint32_t length);
static int32_t IICwriteBytes(uint8_t dev, uint8_t reg, uint8_t* data, uint32_t length);
static void Delayms(uint16_t ucMs);

void setup() {
  // put your setup code here, to run once:
  Wire.begin();
  Wire.setClock(100000);
	Serial.begin(9600);
	WitInit(WIT_PROTOCOL_I2C, 0x50);
	WitI2cFuncRegister(IICwriteBytes, IICreadBytes);
	WitRegisterCallBack(CopeSensorData);
  WitDelayMsRegister(Delayms);
	Serial.print(F("\r\n********************** wit-motion IIC example  ************************\r\n"));
	AutoScanSensor();
}
int i;
float fAcc[3], fGyro[3], fAngle[3];
void loop() {
    while (Serial.available()) 
    {
      CopeCmdData(Serial.read());
    }
		CmdProcess();

    for(uint8_t ucSensorIndex = 0; ucSensorIndex < s_ucSensorNum; ucSensorIndex++)
    {
      WitInit(WIT_PROTOCOL_I2C, s_ucSensorAddr[ucSensorIndex]);
      s_cDataUpdate = 0;
      WitReadReg(AX, 12);
      delay(20);

		if(s_cDataUpdate)
		{
			for(i = 0; i < 3; i++)
			{
				fAcc[i] = (int16_t)sReg[AX+i] / 32768.0f * 16.0f;
				fGyro[i] = (int16_t)sReg[GX+i] / 32768.0f * 2000.0f;
				fAngle[i] = (int16_t)sReg[Roll+i] / 32768.0f * 180.0f;
			}
			if(s_cDataUpdate & ACC_UPDATE)
			{
				Serial.print(F("sensor"));
				Serial.print(ucSensorIndex + 1);
				Serial.print(F("[0x"));
				Serial.print(s_ucSensorAddr[ucSensorIndex], HEX);
				Serial.print(F("] "));
				Serial.print(F("acc:"));
				Serial.print(fAcc[0], 3);
				Serial.print(F(" "));
				Serial.print(fAcc[1], 3);
				Serial.print(F(" "));
				Serial.print(fAcc[2], 3);
				Serial.print(F("\r\n"));
				s_cDataUpdate &= ~ACC_UPDATE;
			}
			if(s_cDataUpdate & GYRO_UPDATE)
			{
				Serial.print(F("sensor"));
				Serial.print(ucSensorIndex + 1);
				Serial.print(F("[0x"));
				Serial.print(s_ucSensorAddr[ucSensorIndex], HEX);
				Serial.print(F("] "));
				Serial.print(F("gyro:"));
				Serial.print(fGyro[0], 1);
				Serial.print(F(" "));
				Serial.print(fGyro[1], 1);
				Serial.print(F(" "));
				Serial.print(fGyro[2], 1);
				Serial.print(F("\r\n"));
				s_cDataUpdate &= ~GYRO_UPDATE;
			}
			if(s_cDataUpdate & ANGLE_UPDATE)
			{
				Serial.print(F("sensor"));
				Serial.print(ucSensorIndex + 1);
				Serial.print(F("[0x"));
				Serial.print(s_ucSensorAddr[ucSensorIndex], HEX);
				Serial.print(F("] "));
				Serial.print(F("angle:"));
				Serial.print(fAngle[0], 3);
				Serial.print(F(" "));
				Serial.print(fAngle[1], 3);
				Serial.print(F(" "));
				Serial.print(fAngle[2], 3);
				Serial.print(F("\r\n"));
				s_cDataUpdate &= ~ANGLE_UPDATE;
			}
			if(s_cDataUpdate & MAG_UPDATE)
			{
				Serial.print(F("sensor"));
				Serial.print(ucSensorIndex + 1);
				Serial.print(F("[0x"));
				Serial.print(s_ucSensorAddr[ucSensorIndex], HEX);
				Serial.print(F("] "));
				Serial.print(F("mag:"));
				Serial.print(sReg[HX]);
				Serial.print(F(" "));
				Serial.print(sReg[HY]);
				Serial.print(F(" "));
				Serial.print(sReg[HZ]);
				Serial.print(F("\r\n"));
				s_cDataUpdate &= ~MAG_UPDATE;
			}
      s_cDataUpdate = 0;
		}
    }

    delay(500);
}


void CopeCmdData(unsigned char ucData)
{
	static unsigned char s_ucData[50], s_ucRxCnt = 0;
	
	s_ucData[s_ucRxCnt++] = ucData;
	if(s_ucRxCnt<3)return;										//Less than three data returned
	if(s_ucRxCnt >= 50) s_ucRxCnt = 0;
	if(s_ucRxCnt >= 3)
	{
		if((s_ucData[1] == '\r') && (s_ucData[2] == '\n'))
		{
			s_cCmd = s_ucData[0];
			memset(s_ucData,0,50);
			s_ucRxCnt = 0;
		}
		else 
		{
			s_ucData[0] = s_ucData[1];
			s_ucData[1] = s_ucData[2];
			s_ucRxCnt = 2;
			
		}
	}
}

static int32_t IICreadBytes(uint8_t dev, uint8_t reg, uint8_t *data, uint32_t length)
{
	int val;
    Wire.beginTransmission(dev);
    Wire.write(reg);
    Wire.endTransmission(false); //endTransmission but keep the connection active

    val = Wire.requestFrom(dev, length); //Ask for bytes, once done, bus is released by default

	if(val == 0)return 0;
    while(Wire.available() < length) //Hang out until we get the # of bytes we expect
    {
      if(Wire.getWireTimeoutFlag())
      {
        Wire.clearWireTimeoutFlag();
        return 0;
      }
    }

    for(int x = 0 ; x < length ; x++)    data[x] = Wire.read();   

    return 1;
}


static int32_t IICwriteBytes(uint8_t dev, uint8_t reg, uint8_t* data, uint32_t length)
{
    Wire.beginTransmission(dev);
    Wire.write(reg);
    Wire.write(data, length);
    if(Wire.getWireTimeoutFlag())
    {
      Wire.clearWireTimeoutFlag();
      return 0;
    }
    Wire.endTransmission(); //Stop transmitting

    return 1; 
}

static void ShowHelp(void)
{
	Serial.print(F("\r\n************************	 WIT_SDK_DEMO	************************"));
	Serial.print(F("\r\n************************          HELP           ************************\r\n"));
	Serial.print(F("UART SEND:a\\r\\n   Acceleration calibration.\r\n"));
	Serial.print(F("UART SEND:m\\r\\n   Magnetic field calibration,After calibration send:   e\\r\\n   to indicate the end\r\n"));
	Serial.print(F("UART SEND:U\\r\\n   Bandwidth increase.\r\n"));
	Serial.print(F("UART SEND:u\\r\\n   Bandwidth reduction.\r\n"));
	Serial.print(F("UART SEND:B\\r\\n   Baud rate increased to 115200.\r\n"));
	Serial.print(F("UART SEND:b\\r\\n   Baud rate reduction to 9600.\r\n"));
	Serial.print(F("UART SEND:h\\r\\n   help.\r\n"));
	Serial.print(F("******************************************************************************\r\n"));
}

static void CmdProcess(void)
{
	switch(s_cCmd)
	{
		case 'a':	if(WitStartAccCali() != WIT_HAL_OK) Serial.print(F("\r\nSet AccCali Error\r\n"));
			break;
		case 'm':	if(WitStartMagCali() != WIT_HAL_OK) Serial.print(F("\r\nSet MagCali Error\r\n"));
			break;
		case 'e':	if(WitStopMagCali() != WIT_HAL_OK) Serial.print(F("\r\nSet MagCali Error\r\n"));
			break;
		case 'u':	if(WitSetBandwidth(BANDWIDTH_5HZ) != WIT_HAL_OK) Serial.print(F("\r\nSet Bandwidth Error\r\n"));
			break;
		case 'U':	if(WitSetBandwidth(BANDWIDTH_256HZ) != WIT_HAL_OK) Serial.print(F("\r\nSet Bandwidth Error\r\n"));
			break;
    case 'B': if(WitSetUartBaud(WIT_BAUD_115200) != WIT_HAL_OK) Serial.print(F("\r\nSet Baud Error\r\n"));
              else Serial.print(F(" 115200 Baud rate modified successfully\r\n"));
      break;
    case 'b': if(WitSetUartBaud(WIT_BAUD_9600) != WIT_HAL_OK) Serial.print(F("\r\nSet Baud Error\r\n"));
              else Serial.print(F(" 9600 Baud rate modified successfully\r\n"));
      break;
		case 'h':	ShowHelp();
			break;
		default :return;
	}
	s_cCmd = 0xff;
}

static void CopeSensorData(uint32_t uiReg, uint32_t uiRegNum)
{
	int i;
    for(i = 0; i < uiRegNum; i++)
    {
        switch(uiReg)
        {
            case AZ:
				s_cDataUpdate |= ACC_UPDATE;
            break;
            case GZ:
				s_cDataUpdate |= GYRO_UPDATE;
            break;
            case HZ:
				s_cDataUpdate |= MAG_UPDATE;
            break;
            case Yaw:
				s_cDataUpdate |= ANGLE_UPDATE;
            break;
            default:
				s_cDataUpdate |= READ_UPDATE;
			break;
        }
		uiReg++;
    }
}

static void Delayms(uint16_t ucMs)
{
  delay(ucMs);
}


static void AutoScanSensor(void)
{
	int i, iRetry;
	
  s_ucSensorNum = 0;
	for(i = 1; i < 0x7F; i++)
	{
		WitInit(WIT_PROTOCOL_I2C, i);
		iRetry = 2;
		do
		{
			s_cDataUpdate = 0;
			WitReadReg(AX, 3);
			delay(5);
			if(s_cDataUpdate != 0)
			{
				Serial.print(F("find 0x"));
				Serial.print(i, HEX);
				Serial.print(F(" addr sensor\r\n"));
        if(s_ucSensorNum < MAX_SENSOR_NUM)
        {
          s_ucSensorAddr[s_ucSensorNum++] = i;
        }
        break;
			}
			iRetry--;
		}while(iRetry);		

    if(s_ucSensorNum >= MAX_SENSOR_NUM)
    {
      break;
    }
	}

  if(s_ucSensorNum > 0)
  {
    WitInit(WIT_PROTOCOL_I2C, s_ucSensorAddr[0]);
    Serial.print(F("sensor count:"));
    Serial.print(s_ucSensorNum);
    Serial.print(F("\r\n"));
    ShowHelp();
    return;
  }

	Serial.print(F("can not find sensor\r\n"));
	Serial.print(F("please check your connection\r\n"));
}
